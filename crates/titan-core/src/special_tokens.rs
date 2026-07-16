//! Special token management.

use crate::TokenId;

#[derive(Debug, Clone, Default)]
pub struct SpecialTokenSet {
    pub tokens: Vec<(String, TokenId)>,
}

impl SpecialTokenSet {
    pub fn default_set() -> Self {
        Self {
            tokens: vec![
                ("<PAD>".into(), 0),
                ("<UNK>".into(), 1),
                ("<BOS>".into(), 2),
                ("<EOS>".into(), 3),
                ("<MASK>".into(), 4),
            ],
        }
    }

    pub fn id(&self, token: &str) -> Option<TokenId> {
        self.tokens.iter().find(|(t, _)| t == token).map(|(_, id)| *id)
    }

    pub fn token(&self, id: TokenId) -> Option<&str> {
        self.tokens.iter().find(|(_, i)| *i == id).map(|(t, _)| t.as_str())
    }

    pub fn add(&mut self, token: impl Into<String>) -> TokenId {
        let token = token.into();
        if let Some(id) = self.id(&token) {
            return id;
        }
        let id = self.tokens.len() as TokenId;
        self.tokens.push((token, id));
        id
    }
}

pub fn list_special_tokens() -> SpecialTokenSet {
    SpecialTokenSet::default_set()
}

pub fn add_special_tokens(set: &mut SpecialTokenSet, tokens: &[&str]) -> Vec<TokenId> {
    tokens.iter().map(|t| set.add(*t)).collect()
}
