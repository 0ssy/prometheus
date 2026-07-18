from __future__ import annotations

from enterprise import (
    OrganizationRegistry,
    ProjectRegistry,
    RoleRegistry,
    TeamRegistry,
    UserRegistry,
)


def test_organization_registry_create_and_get():
    registry = OrganizationRegistry()
    org = registry.create("Acme", metadata={"tier": "pro"})
    assert org.name == "Acme"
    assert registry.get(org.org_id) is org
    assert org.metadata["tier"] == "pro"
    assert len(registry.list_all()) == 1


def test_project_registry_create_and_list():
    orgs = OrganizationRegistry()
    projects = ProjectRegistry()
    org = orgs.create("Acme")
    p1 = projects.create(org.org_id, "Alpha")
    p2 = projects.create(org.org_id, "Beta")
    assert projects.get(p1.project_id).name == "Alpha"
    listed = projects.list_by_org(org.org_id)
    assert {p.project_id for p in listed} == {p1.project_id, p2.project_id}


def test_user_registry_create_and_get_by_email():
    orgs = OrganizationRegistry()
    users = UserRegistry()
    org = orgs.create("Acme")
    user = users.create("alice@example.com", "Alice", org.org_id)
    assert users.get(user.user_id) is user
    assert users.get_by_email("alice@example.com") is user
    assert users.get_by_email("missing@example.com") is None


def test_team_registry_add_member():
    orgs = OrganizationRegistry()
    teams = TeamRegistry()
    users = UserRegistry()
    org = orgs.create("Acme")
    team = teams.create(org.org_id, "Core")
    user = users.create("bob@example.com", "Bob", org.org_id)
    teams.add_member(team.team_id, user.user_id)
    assert user.user_id in teams.get(team.team_id).member_ids
    teams.remove_member(team.team_id, user.user_id)
    assert user.user_id not in teams.get(team.team_id).member_ids


def test_role_registry_permissions():
    orgs = OrganizationRegistry()
    roles = RoleRegistry()
    org = orgs.create("Acme")
    base = roles.create(org.org_id, "viewer", permissions={"device.read"})
    elevated = roles.create(org.org_id, "operator", permissions={"device.write"}, inherits=[base.role_id])
    effective = roles.get_effective_permissions(elevated.role_id)
    assert effective == {"device.read", "device.write"}
    roles.add_permission(base.role_id, "knowledge.read")
    assert "knowledge.read" in roles.get_effective_permissions(base.role_id)
