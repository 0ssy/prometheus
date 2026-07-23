use std::collections::HashMap;
use std::path::Path;
use std::sync::{Mutex, MutexGuard};

use rusqlite::Connection;
use serde_json::Value;
use uuid::Uuid;

use crate::error::KernelResult;

/// Persisted window layout/state for one open app window.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize)]
pub struct WindowState {
    pub id: String,
    pub app_id: String,
    pub x: i32,
    pub y: i32,
    pub width: i32,
    pub height: i32,
    pub minimized: bool,
    pub maximized: bool,
    #[serde(default)]
    pub z_order: i32,
}

/// A persisted workspace session: which apps/windows were open and which
/// terminal sessions existed, so the desktop can restore after restart.
#[derive(Debug, Clone, serde::Serialize, serde::Deserialize, Default)]
pub struct Session {
    pub id: String,
    pub windows: Vec<WindowState>,
    #[serde(default)]
    pub terminals: Vec<String>,
    #[serde(default)]
    pub meta: HashMap<String, Value>,
}

impl Session {
    pub fn new() -> Self {
        Self {
            id: Uuid::new_v4().to_string(),
            windows: Vec::new(),
            terminals: Vec::new(),
            meta: HashMap::new(),
        }
    }
}

/// Persists workspace state to a SQLite file via Tauri's app path. Python
/// remains the single writer of the main platform DB; this is a dedicated
/// sessions DB so Rust never contends for the same file.
pub struct SessionManager {
    conn: Mutex<Connection>,
}

impl SessionManager {
    /// Open (creating if needed) the sessions DB at `path`.
    pub fn open<P: AsRef<Path>>(path: P) -> KernelResult<Self> {
        let conn = Connection::open(path)?;
        let mgr = Self {
            conn: Mutex::new(conn),
        };
        mgr.migrate()?;
        Ok(mgr)
    }

    fn migrate(&self) -> KernelResult<()> {
        self.conn.lock().unwrap().execute_batch(
            "CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                data TEXT NOT NULL,
                updated_at INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS windows (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                app_id TEXT NOT NULL,
                data TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_windows_session ON windows(session_id);",
        )?;
        Ok(())
    }

    /// Save (upsert) a full session: replaces windows for that session id.
    pub fn save(&self, session: &Session) -> KernelResult<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        let data = serde_json::to_string(session)?;
        tx.execute(
            "INSERT INTO sessions (id, data, updated_at) VALUES (?1, ?2, strftime('%s','now'))
             ON CONFLICT(id) DO UPDATE SET data = excluded.data, updated_at = strftime('%s','now')",
            rusqlite::params![session.id, data],
        )?;
        tx.execute("DELETE FROM windows WHERE session_id = ?1", [session.id.clone()])?;
        for w in &session.windows {
            let wdata = serde_json::to_string(w)?;
            tx.execute(
                "INSERT INTO windows (id, session_id, app_id, data) VALUES (?1, ?2, ?3, ?4)",
                rusqlite::params![w.id, session.id, w.app_id, wdata],
            )?;
        }
        tx.commit()?;
        Ok(())
    }

    /// Load a session by id. `None` if absent (caller may create a fresh one).
    pub fn load(&self, id: &str) -> KernelResult<Option<Session>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn.prepare("SELECT data FROM sessions WHERE id = ?1")?;
        let mut rows = stmt.query([id])?;
        match rows.next()? {
            Some(row) => {
                let data: String = row.get(0)?;
                let mut session: Session = serde_json::from_str(&data)?;
                session.windows = Self::read_windows(&conn, id)?;
                Ok(Some(session))
            }
            None => Ok(None),
        }
    }

    /// Read window rows for a session from the `windows` table.
    fn read_windows(conn: &MutexGuard<Connection>, session_id: &str) -> KernelResult<Vec<WindowState>> {
        let mut stmt = conn.prepare("SELECT data FROM windows WHERE session_id = ?1")?;
        let mut rows = stmt.query([session_id])?;
        let mut out = Vec::new();
        while let Some(row) = rows.next()? {
            let data: String = row.get(0)?;
            out.push(serde_json::from_str(&data)?);
        }
        Ok(out)
    }

    /// Return the most recently updated session, if any.
    pub fn latest(&self) -> KernelResult<Option<Session>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT data FROM sessions ORDER BY rowid DESC LIMIT 1")?;
        let mut rows = stmt.query([])?;
        match rows.next()? {
            Some(row) => {
                let data: String = row.get(0)?;
                let mut session: Session = serde_json::from_str(&data)?;
                session.windows = Self::read_windows(&conn, &session.id)?;
                Ok(Some(session))
            }
            None => Ok(None),
        }
    }

    /// Upsert a single window within a session (used during live editing).
    pub fn save_window(&self, session_id: &str, window: &WindowState) -> KernelResult<()> {
        // Ensure the session row exists.
        if self.load(session_id)?.is_none() {
            let mut s = Session::new();
            s.id = session_id.to_string();
            self.save(&s)?;
        }
        let wdata = serde_json::to_string(window)?;
        self.conn.lock().unwrap().execute(
            "INSERT INTO windows (id, session_id, app_id, data) VALUES (?1, ?2, ?3, ?4)
             ON CONFLICT(id) DO UPDATE SET session_id = excluded.session_id,
                                         app_id = excluded.app_id,
                                         data = excluded.data",
            rusqlite::params![window.id, session_id, window.app_id, wdata],
        )?;
        Ok(())
    }

    /// Remove a window from its session.
    pub fn remove_window(&self, window_id: &str) -> KernelResult<()> {
        self.conn
            .lock()
            .unwrap()
            .execute("DELETE FROM windows WHERE id = ?1", [window_id])?;
        Ok(())
    }

    /// List all saved sessions (ids + updated_at), newest first.
    pub fn list_sessions(&self) -> KernelResult<Vec<(String, i64)>> {
        let conn = self.conn.lock().unwrap();
        let mut stmt = conn
            .prepare("SELECT id, updated_at FROM sessions ORDER BY updated_at DESC")?;
        let rows = stmt.query_map([], |row| Ok((row.get::<_, String>(0)?, row.get::<_, i64>(1)?)))?;
        let mut out = Vec::new();
        for r in rows {
            out.push(r?);
        }
        Ok(out)
    }

    /// Delete a saved session and its windows.
    pub fn delete(&self, id: &str) -> KernelResult<()> {
        let mut conn = self.conn.lock().unwrap();
        let tx = conn.transaction()?;
        tx.execute("DELETE FROM windows WHERE session_id = ?1", [id])?;
        tx.execute("DELETE FROM sessions WHERE id = ?1", [id])?;
        tx.commit()?;
        Ok(())
    }

    /// Build a Session from the currently tracked windows and terminal ids,
    /// then save it.
    pub fn snapshot_and_save(
        &self,
        id: &str,
        windows: Vec<WindowState>,
        terminals: Vec<String>,
    ) -> KernelResult<Session> {
        let session = match self.load(id)? {
            Some(mut s) => {
                s.windows = windows;
                s.terminals = terminals;
                s
            }
            None => Session {
                id: id.to_string(),
                windows,
                terminals,
                meta: HashMap::new(),
            },
        };
        self.save(&session)?;
        Ok(session)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn temp_db() -> std::path::PathBuf {
        let dir = std::env::temp_dir();
        let name = format!("prometheus-kernel-test-{}.db", uuid::Uuid::new_v4());
        dir.join(name)
    }

    #[test]
    fn save_and_load_round_trips() {
        let path = temp_db();
        let mgr = SessionManager::open(&path).unwrap();
        let mut s = Session::new();
        s.windows.push(WindowState {
            id: "w1".into(),
            app_id: "terminal".into(),
            x: 10,
            y: 20,
            width: 800,
            height: 600,
            minimized: false,
            maximized: false,
            z_order: 1,
        });
        s.terminals.push("t1".into());
        mgr.save(&s).unwrap();

        let loaded = mgr.load(&s.id).unwrap().expect("session present");
        assert_eq!(loaded.windows.len(), 1);
        assert_eq!(loaded.windows[0].app_id, "terminal");
        assert_eq!(loaded.windows[0].x, 10);
        assert_eq!(loaded.terminals, vec!["t1".to_string()]);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn latest_returns_most_recent() {
        let path = temp_db();
        let mgr = SessionManager::open(&path).unwrap();
        let mut a = Session::new();
        a.id = "a".into();
        let mut b = Session::new();
        b.id = "b".into();
        mgr.save(&a).unwrap();
        std::thread::sleep(std::time::Duration::from_millis(10));
        mgr.save(&b).unwrap();

        let latest = mgr.latest().unwrap().expect("has latest");
        assert_eq!(latest.id, "b");

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn window_upsert_and_remove() {
        let path = temp_db();
        let mgr = SessionManager::open(&path).unwrap();
        let w = WindowState {
            id: "w1".into(),
            app_id: "files".into(),
            x: 0,
            y: 0,
            width: 640,
            height: 480,
            minimized: false,
            maximized: false,
            z_order: 0,
        };
        mgr.save_window("s1", &w).unwrap();

        let s = mgr.load("s1").unwrap().expect("session auto-created");
        assert_eq!(s.windows.len(), 1);

        mgr.remove_window("w1").unwrap();
        let s = mgr.load("s1").unwrap().unwrap();
        assert_eq!(s.windows.len(), 0);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn snapshot_and_save_merges() {
        let path = temp_db();
        let mgr = SessionManager::open(&path).unwrap();
        let w = WindowState {
            id: "w1".into(),
            app_id: "terminal".into(),
            x: 1,
            y: 2,
            width: 3,
            height: 4,
            minimized: false,
            maximized: false,
            z_order: 0,
        };
        let s = mgr
            .snapshot_and_save("s1", vec![w], vec!["t1".into()])
            .unwrap();
        assert_eq!(s.terminals, vec!["t1".to_string()]);
        assert_eq!(s.windows[0].width, 3);

        let _ = std::fs::remove_file(&path);
    }

    #[test]
    fn delete_removes_session_and_windows() {
        let path = temp_db();
        let mgr = SessionManager::open(&path).unwrap();
        let mut s = Session::new();
        s.id = "del".into();
        s.windows.push(WindowState {
            id: "w".into(),
            app_id: "x".into(),
            x: 0,
            y: 0,
            width: 1,
            height: 1,
            minimized: false,
            maximized: false,
            z_order: 0,
        });
        mgr.save(&s).unwrap();
        mgr.delete("del").unwrap();
        assert!(mgr.load("del").unwrap().is_none());

        let _ = std::fs::remove_file(&path);
    }
}
