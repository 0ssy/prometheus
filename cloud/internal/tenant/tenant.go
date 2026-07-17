package tenant

type Tenant struct {
	ID       string
	Name     string
	TeamIDs  []string
	APIKey   string
	Created  int64
}

type Team struct {
	ID       string
	TenantID string
	Name     string
	MemberIDs []string
}

type Member struct {
	ID       string
	TeamID   string
	Email    string
	Role     string
}
