from mcp.server.fastmcp import FastMCP
from neo4j import GraphDatabase
import json
from typing import List, Dict, Any, Optional
import inspect
import os

# Create an MCP server
mcp = FastMCP("BloodHound", port=3000)

# 環境變數設定
BLOODHOUND_URI = os.getenv("BLOODHOUND_URI", "bolt://localhost:7687")
BLOODHOUND_USERNAME = os.getenv("BLOODHOUND_USERNAME", "neo4j")
BLOODHOUND_PASSWORD = os.getenv("BLOODHOUND_PASSWORD", "bloodhound")

@mcp.prompt()
def prompt():
    p = """
# System Prompt for MCP Server Script

You are an AI assistant integrated with the MCP Server, designed to help users query and analyze Active Directory (AD) and Azure Active Directory (AAD) environments using a Neo4j database populated with BloodHound data. Your primary role is to assist users by executing predefined queries or crafting custom queries to retrieve the information they need.

## Available Tools

You have access to a set of predefined tools (Python functions) that correspond to specific BloodHound queries. Each tool is designed to perform a particular task, such as listing users, groups, computers, or finding paths between nodes. These tools are categorized for ease of use:

- **Top 10**: Queries to find top users, computers, or sessions based on specific criteria.
- **Domain / Macro**: Queries to list domains, trusts, users, computers, and other macro-level information.
- **Owned**: Queries related to owned users, computers, and their relationships.
- **Non-privileged**: Queries focusing on non-privileged users and their permissions.
- **Privilege Escalation / Lateral Movement**: Queries to identify potential privilege escalation paths and lateral movement opportunities.
- **Privileged**: Queries related to privileged users and groups.
- **Persistence**: Queries to find persistence mechanisms like dangerous rights to AdminSDHolder or DCSync capabilities.
- **AAD**: Queries specific to Azure Active Directory, including tenancy, groups, and privileged access.

Each tool is accessible via a unique identifier, such as `tool://users_with_most_local_admin_rights`, and may require parameters like the domain name.

## Using Tools

When a user asks a question or requests information, your first step is to determine which predefined tool(s) can be used to answer the query. For example:

- If a user asks for "users with the most local admin rights in domain X," you should use the `users_with_most_local_admin_rights` tool with the specified domain.
- If a user wants to "list all enabled users in domain Y," you should use the `list_enabled_users` tool with the appropriate domain.

Many tools require a domain parameter. If the user does not specify a domain, you should attempt to infer it from the context or query the database to find relevant domains. If you cannot determine the domain, ask the user for clarification.

## Handling Parameters

- **Domain Parameter**: Most tools require a domain name. If not provided, try to:
  - Check if the user has previously mentioned a domain.
  - Query the database to list available domains using `list_domains` and ask the user to specify one.
- **Other Parameters**: Some tools may require additional parameters (e.g., specific object names). If these are missing, attempt to resolve them by querying related information or ask the user for more details.

## Custom Queries

If the predefined tools do not suffice for a user's request, you can write and execute custom Neo4j Cypher queries using the `run_query` tool (`tool://run_query`). This allows you to handle complex or unique queries that are not covered by the predefined functions.

- **When to Use Custom Queries**: Use custom queries when:
  - The user's request does not match any predefined tool.
  - The request requires combining multiple queries or filtering results in a specific way.
- **Writing Custom Queries**: Ensure that your custom queries are correctly formatted Cypher queries. You can use the Neo4j documentation or examples from the predefined queries as a reference.
**Note**:
When users inquire whether a specific account (e.g., 'user@domain.LOCAL') has permissions to modify other objects (such as other users, computers, etc.), you will need to write a Cypher query similar to the one below to check these permissions. These permissions might include `GenericWrite`, `GenericAll`, `WriteDacl`, `WriteOwner`, etc., and multiple queries may be necessary.

### ***Custom Query Example**:
```cypher
MATCH p=(u1:User {name: 'user@domain.LOCAL'})-[:MemberOf*0..]->()-[:GenericWrite]->(u2:User)
RETURN DISTINCT u2.name```

**Description**:
This query is used to check if the user 'user@domain.LOCAL' has the `GenericWrite` permission on other users through their group membership relationships. You can adjust the type of permission or the type of target object according to your needs.


## Error Handling and Missing Information

- **Missing Parameters**: If a required parameter is missing, try to resolve it by:
  - Querying the database for possible values (e.g., listing domains or objects).
  - Asking the user for the missing information.
- **Query Failures**: If a query fails or returns no results, consider:
  - Rephrasing the query or adjusting parameters.
  - Checking for typos or incorrect assumptions in the query.
  - Informing the user that no results were found and asking for clarification.
- **Ambiguous Requests**: If a user's request is ambiguous, ask for more details to ensure you understand their needs correctly.

## Examples

- **User Request**: "Find users with the most local admin rights in domain CONTOSO."
  - **Action**: Use `users_with_most_local_admin_rights` with `domain='CONTOSO'`.
- **User Request**: "List all domains."
  - **Action**: Use `list_domains` (no parameters needed).
- **User Request**: "Find paths from owned users to high-value targets in domain FABRIKAM."
  - **Action**: Use `route_from_owned_enabled_principals_to_high_value_targets` with `domain='FABRIKAM'`.
- **User Request**: "Show me all users who can perform DCSync."
  - **Action**: Since there is no predefined tool, write a custom query using `run_query` to find users with DCSync rights.

## Guidelines

- **Be Proactive**: Try to resolve missing information or ambiguities by querying the database or inferring from context before asking the user.
- **Be Clear**: When asking the user for clarification, be specific about what information is needed.
- **Be Efficient**: Use the most direct tool or query to answer the user's request.
- **Be Informative**: Provide context or explanations when necessary, especially for complex queries or results.
- **注意大小寫，Neo4j 有大小寫之分**
- **優先使用內建的工具，如果沒有再進行 Custom Query**
    - route_non_privileged_users_with_dangerous_permissions 是一個非常常使用的工具，請優先使用
    - 使用 Custom Query 時，請務必使用不同的 Query String 執行 3 次並統整答案
- 請多使用不同的工具組合，使用越多越好，盡可能不要單純只用一個來完成事情

## Tone and Style

Maintain a professional, helpful, and instructive tone. Your responses should be clear, concise, and focused on assisting the user in understanding and navigating the AD and AAD environments.

"""
    return p

@mcp.tool("tool://run_query")
def run_query(query: str, parameters: Optional[Dict[str, Any]] = None) -> List[Dict[str, Any]]:
    """
    執行Cypher查詢並返回結果
    
    Args:
        query: Cypher查詢字符串
        parameters: 查詢參數字典
        
    Returns:
        查詢結果列表
    """
    driver = GraphDatabase.driver(
        BLOODHOUND_URI, 
        auth=(BLOODHOUND_USERNAME, BLOODHOUND_PASSWORD)
    )
    try:
        with driver.session() as session:
            result = session.run(query, parameters or {})
            return [record.data() for record in result]
    finally:
        driver.close()

@mcp.tool("tool://users_with_most_local_admin_rights")
def users_with_most_local_admin_rights(domain):
    """
    [WIP] Users with Most Local Admin Rights
    """
    query = "MATCH (n:User {domain: '%s'}),(m:Computer), (n)-[r:AdminTo]->(m) WHERE NOT n.name STARTS WITH 'ANONYMOUS LOGON' AND NOT n.name='' WITH n, count(r) as rel_count order by rel_count desc LIMIT 10 MATCH p=(m)<-[r:AdminTo]-(n) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://computers_with_most_sessions")
def computers_with_most_sessions(domain):
    """
    [WIP] Computers with Most Sessions [Required: sessions]
    """
    # Note: The provided query seems incorrect (matches Users with AdminTo instead of Computers with HasSession).
    # Correcting based on the name and intent.
    query = "MATCH (m:Computer {domain: '%s'}),(n:User), (m)-[r:HasSession]->(n) WHERE NOT n.name STARTS WITH 'ANONYMOUS LOGON' AND NOT n.name='' WITH m, count(r) as rel_count order by rel_count desc LIMIT 10 MATCH p=(m)-[r:HasSession]->(n) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://users_with_most_sessions")
def users_with_most_sessions(domain):
    """
    [WIP] Users with Most Sessions [Required: sessions]
    """
    query = "MATCH (n:User {domain: '%s'}),(m:Computer), (n)<-[r:HasSession]-(m) WHERE NOT n.name STARTS WITH 'ANONYMOUS LOGON' AND NOT n.name='' WITH n, count(r) as rel_count order by rel_count desc LIMIT 10 MATCH p=(m)-[r:HasSession]->(n) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://non_privileged_users_with_dangerous_permissions")
def non_privileged_users_with_dangerous_permissions(domain):
    """
    List non-privileged user(s) with dangerous permissions to any node type
    """
    query = "MATCH (u:User {enabled: true, admincount: false, domain: '%s'})-[r]->(a) RETURN u, COUNT(DISTINCT type(r)) AS permissions ORDER BY permissions DESC LIMIT 10" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_permissions")
def route_non_privileged_users_with_dangerous_permissions(domain):
    """
    Route non-privileged user(s) with dangerous permissions to any node type
    """
    query = "MATCH (u:User {enabled: true, admincount: false, domain: '%s'})-[r]->(a) WITH u, COUNT(DISTINCT type(r)) AS permissions ORDER BY permissions DESC LIMIT 10 MATCH p=allshortestpaths((u)-[r]->(a)) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://users_with_most_cross_domain_sessions")
def users_with_most_cross_domain_sessions(domain):
    """
    [WIP] Users with most cross-domain sessions [Required: sessions]
    """
    query = "MATCH p=(g1:Group)<-[:MemberOf*1..]-(u:User {enabled:true, domain: '%s'})<-[r:HasSession]-(c:Computer) WHERE NOT u.domain = c.domain WITH u, count(r) as rel_count order by rel_count desc LIMIT 10 MATCH p=(c:Computer)-[r:HasSession]->(u) WHERE NOT u.domain = c.domain RETURN p ORDER BY c.name" % domain
    return run_query(query)


@mcp.tool("tool://list_high_value_targets")
def list_high_value_targets(domain):
    """
    List high value target(s)
    """
    query = "MATCH (a {highvalue: true, domain: '%s'}) RETURN a" % domain
    return run_query(query)

@mcp.tool("tool://list_domains")
def list_domains():
    """
    List domain(s)
    """
    query = "MATCH (d:Domain) RETURN d"
    return run_query(query)

@mcp.tool("tool://list_domain_trusts")
def list_domain_trusts():
    """
    List domain trust(s)
    """
    query = "MATCH p=(n:Domain)-->(m:Domain) RETURN p"
    return run_query(query)

@mcp.tool("tool://list_enabled_users")
def list_enabled_users(domain):
    """
    List enabled user(s)
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_users_with_email")
def list_enabled_users_with_email(domain):
    """
    List enabled user(s) with an email address
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE exists(u.email) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_non_managed_service_accounts")
def list_non_managed_service_accounts(domain):
    """
    List non-managed service account(s)
    """
    query = "MATCH (u:User {hasspn:true, domain: '%s'}) WHERE NOT u.name CONTAINS '$' AND NOT u.name CONTAINS 'KRBTGT' RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_principals_with_unconstrained_delegation")
def list_enabled_principals_with_unconstrained_delegation(domain):
    """
    List enabled principal(s) with \"Unconstrained Delegation\"
    """
    query = "MATCH (a {unconstraineddelegation: true, enabled: true, domain: '%s'}) RETURN a" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_principals_with_constrained_delegation")
def list_enabled_principals_with_constrained_delegation(domain):
    """
    List enabled principal(s) with \"Constrained Delegation\"
    """
    query = "MATCH (a {enabled: true, domain: '%s'}) WHERE exists(a.`allowedtodelegate`) RETURN a" % domain
    return run_query(query)

@mcp.tool("tool://list_domain_controllers")
def list_domain_controllers(domain):
    """
    List domain controller(s)
    """
    query = "MATCH (c:Computer {domain: '%s'})-[:MemberOf]->(g:Group) WHERE g.samaccountname CONTAINS 'Domain Controllers' RETURN c" % domain
    return run_query(query)

@mcp.tool("tool://list_domain_computers")
def list_domain_computers(domain):
    """
    List domain computer(s)
    """
    query = "MATCH (c:Computer {domain: '%s'}) RETURN c" % domain
    return run_query(query)

@mcp.tool("tool://list_certificate_authority_servers")
def list_certificate_authority_servers(domain):
    """
    List Certificate Authority server(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {type:'Enrollment Service', domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_privileges_for_certificate_authority_servers")
def list_privileges_for_certificate_authority_servers(domain):
    """
    [WIP] List privileges for Certificate Authority server(s) [Required: Certipy]
    """
    # Note: This query has an intermediate step requiring a CA selection ($result in final query).
    # For simplicity, assuming domain-level execution; adjust if CA name is parameterized differently.
    query = "MATCH p=(g)-[:ManageCa|ManageCertificates|Auditor|Operator|Read|Enroll]->(n:GPO {type:'Enrollment Service', domain: '%s'}) return p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_certificate_templates")
def list_all_certificate_templates(domain):
    """
    List all Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {type:'Certificate Template', domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://find_enabled_certificate_templates")
def find_enabled_certificate_templates(domain):
    """
    Find enabled Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {enabled:true, type:'Certificate Template', domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enrollment_rights_for_certificate_templates")
def list_all_enrollment_rights_for_certificate_templates(domain):
    """
    [WIP] List all Enrollment Right(s) for Certificate Template(s)
    """
    # Note: Requires a template selection step; simplified to domain scope here.
    query = "MATCH p=(g)-[:Enroll|AutoEnroll]->(n:GPO {type:'Certificate Template', domain: '%s'}) return p" % domain
    return run_query(query)

@mcp.tool("tool://list_computers_without_laps")
def list_computers_without_laps(domain):
    """
    List computer(s) WITHOUT LAPS
    """
    query = "MATCH (c:Computer {haslaps:false, domain: '%s'}) RETURN c ORDER BY c.name" % domain
    return run_query(query)

@mcp.tool("tool://list_network_shares_ignoring_sysvol")
def list_network_shares_ignoring_sysvol(domain):
    """
    List network share(s), ignoring SYSVOL
    """
    query = "MATCH (a {domain: '%s'}) WHERE (any(prop in keys(a) where a[prop] contains '\\\\' and not a[prop] contains 'SYSVOL')) RETURN a" % domain
    return run_query(query)

@mcp.tool("tool://list_all_groups")
def list_all_groups(domain):
    """
    List all group(s)
    """
    query = "MATCH (g:Group {domain: '%s'}) RETURN g" % domain
    return run_query(query)

@mcp.tool("tool://list_all_gpos")
def list_all_gpos(domain):
    """
    List all GPO(s)
    """
    query = "MATCH (g:GPO {domain: '%s'}) RETURN g" % domain
    return run_query(query)

@mcp.tool("tool://list_all_principals_with_local_admin_permission")
def list_all_principals_with_local_admin_permission(domain):
    """
    List all principal(s) with \"Local Admin\" permission
    """
    query = "MATCH p=(a {domain: '%s'})-[:MemberOf|AdminTo*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_principals_with_rdp_permission")
def list_all_principals_with_rdp_permission(domain):
    """
    List all principal(s) with \"RDP\" permission
    """
    query = "MATCH p=(a {domain: '%s'})-[:MemberOf|CanRDP*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_principals_with_sqladmin_permission")
def list_all_principals_with_sqladmin_permission(domain):
    """
    List all principal(s) with \"SQLAdmin\" permission
    """
    query = "MATCH p=(a {domain: '%s'})-[:MemberOf|SQLAdmin*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_user_sessions")
def list_all_user_sessions(domain):
    """
    List all user session(s) [Required: sessions]
    """
    query = "MATCH p=(u:User {domain: '%s'})<-[r:HasSession]-(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_users_with_description_field")
def list_all_users_with_description_field(domain):
    """
    List all user(s) with description field
    """
    query = "MATCH (u:User {domain: '%s'}) WHERE u.description IS NOT null RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_with_userpassword_attribute")
def list_all_enabled_users_with_userpassword_attribute(domain):
    """
    List all enabled user(s) with \"userpassword\" attribute
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE u.userpassword IS NOT null RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_with_password_never_expires")
def list_all_enabled_users_with_password_never_expires(domain):
    """
    List all enabled user(s) with \"password never expires\" attribute
    """
    query = "MATCH (u:User {pwdneverexpires:true, enabled:true, domain: '%s'}) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_with_password_never_expires_not_changed_last_year")
def list_all_enabled_users_with_password_never_expires_not_changed_last_year(domain):
    """
    List all enabled user(s) with \"password never expires\" attribute and not changed in last year
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE u.pwdneverexpires=TRUE AND u.pwdlastset < (datetime().epochseconds - (365 * 86400)) and NOT u.pwdlastset IN [-1.0, 0.0] RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_with_no_password_required")
def list_all_enabled_users_with_no_password_required(domain):
    """
    List all enabled user(s) with \"don't require passwords\" attribute
    """
    query = "MATCH (u:User {passwordnotreqd:true, enabled:true, domain: '%s'}) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_never_logged_in")
def list_all_enabled_users_never_logged_in(domain):
    """
    List all enabled user(s) but never logged in
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE u.lastlogontimestamp=-1.0 RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_logged_in_last_90_days")
def list_all_enabled_users_logged_in_last_90_days(domain):
    """
    List all enabled user(s) that logged in within the last 90 days
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE u.lastlogon < (datetime().epochseconds - (90 * 86400)) and NOT u.lastlogon IN [-1.0, 0.0] RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_set_password_last_90_days")
def list_all_enabled_users_set_password_last_90_days(domain):
    """
    List all enabled user(s) that set password within the last 90 days
    """
    query = "MATCH (u:User {enabled:true, domain: '%s'}) WHERE u.pwdlastset < (datetime().epochseconds - (90 * 86400)) and NOT u.pwdlastset IN [-1.0, 0.0] RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_enabled_users_with_foreign_group_membership")
def list_all_enabled_users_with_foreign_group_membership(domain):
    """
    List all enabled user(s) with foreign group membership
    """
    query = "MATCH p=(u:User {enabled:true, domain: '%s'})-[:MemberOf*1..]->(g:Group) WHERE NOT u.domain = g.domain RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_users")
def list_all_owned_users(domain):
    """
    List all owned user(s)
    """
    query = "MATCH (u:User {owned:true, domain: '%s'}) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_enabled_users")
def list_all_owned_enabled_users(domain):
    """
    List all owned & enabled user(s)
    """
    query = "MATCH (u:User {owned:true, enabled:true, domain: '%s'}) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_enabled_users_with_email")
def list_all_owned_enabled_users_with_email(domain):
    """
    List all owned & enabled user(s) with an email address
    """
    query = "MATCH (u:User {owned:true, enabled:true, domain: '%s'}) WHERE exists(u.email) RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_enabled_users_with_local_admin_and_sessions")
def list_all_owned_enabled_users_with_local_admin_and_sessions(domain):
    """
    List all owned & enabled user(s) with \"Local Admin\" permission, and any active sessions and their group membership(s)
    """
    query = "MATCH p=(u:User {owned:true, enabled: true, domain: '%s'})-[:MemberOf|AdminTo*1..]->(c:Computer) OPTIONAL MATCH p2=(c)-[:HasSession]->(u2:User) OPTIONAL MATCH p3=(u2:User)-[:MemberOf*1..]->(:Group) RETURN p, p2, p3" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_enabled_users_with_rdp_and_sessions")
def list_all_owned_enabled_users_with_rdp_and_sessions(domain):
    """
    List all owned & enabled user(s) with \"RDP\" permission, and any active sessions and their group membership(s)
    """
    query = "MATCH p=(u:User {owned:true, enabled: true, domain: '%s'})-[:MemberOf|CanRDP*1..]->(c:Computer) OPTIONAL MATCH p2=(c)-[:HasSession]->(u2:User) OPTIONAL MATCH p3=(u2:User)-[:MemberOf*1..]->(:Group) RETURN p, p2, p3" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_enabled_users_with_sqladmin")
def list_all_owned_enabled_users_with_sqladmin(domain):
    """
    List all owned & enabled user(s) with \"SQLAdmin\" permission
    """
    query = "MATCH p=(u:User {owned:true, enabled: true, domain: '%s'})-[:MemberOf|SQLAdmin*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_owned_computers")
def list_all_owned_computers(domain):
    """
    List all owned computer(s)
    """
    query = "MATCH (c:Computer {owned:true, domain: '%s'}) RETURN c ORDER BY c.name" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_group_memberships")
def route_all_owned_enabled_group_memberships(domain):
    """
    Route all owned & enabled group membership(s)
    """
    query = "MATCH p=(u:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf*1..]->(g:Group) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_non_privileged_group_memberships")
def route_all_owned_enabled_non_privileged_group_memberships(domain):
    """
    Route all owned & enabled non-privileged group(s) membership
    """
    query = "MATCH p=(u:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf*1..]->(g:Group {admincount:false}) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_privileged_group_memberships")
def route_all_owned_enabled_privileged_group_memberships(domain):
    """
    Route all owned & enabled privileged group(s) membership
    """
    query = "MATCH p=(u:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf*1..]->(g:Group {admincount:true}) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_users_with_dangerous_rights_to_any_node")
def route_all_owned_enabled_users_with_dangerous_rights_to_any_node(domain):
    """
    Route all owned & enabled user(s) with Dangerous Rights to any node type
    """
    query = "MATCH p=allshortestpaths((u:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a)) WHERE NOT a = u RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_users_with_dangerous_rights_to_groups")
def route_all_owned_enabled_users_with_dangerous_rights_to_groups(domain):
    """
    Route all owned & enabled user(s) with Dangerous Rights to group(s)
    """
    query = "MATCH p=allshortestpaths((u:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(:Group)) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_owned_enabled_users_with_dangerous_rights_to_users")
def route_all_owned_enabled_users_with_dangerous_rights_to_users(domain):
    """
    Route all owned & enabled user(s) with Dangerous Rights to user(s)
    """
    query = "MATCH p=allshortestpaths((o:User {owned:true, enabled:true, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(u:User)) WHERE NOT o = u RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_from_owned_enabled_users_to_unconstrained_delegation")
def route_from_owned_enabled_users_to_unconstrained_delegation(domain):
    """
    Route from owned & enabled user(s) to all principals with \"Unconstrained Delegation\"
    """
    query = "MATCH p=allshortestpaths((o:User {owned:true, enabled:true, domain: '%s'})-[*]->(a {unconstraineddelegation: true, enabled: true})) WHERE NOT o = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_from_owned_enabled_principals_to_high_value_targets")
def route_from_owned_enabled_principals_to_high_value_targets(domain):
    """
    Route from owned & enabled principals to high value target(s)
    """
    query = "MATCH p=allShortestPaths((o {owned:true, enabled:true, domain: '%s'})-[*]->(a {highvalue: true})) WHERE NOT o=a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_all_owned_users_with_privileged_access_to_azure_tenancy")
def find_all_owned_users_with_privileged_access_to_azure_tenancy(domain):
    """
    Owned: [WIP] Find all owned user with privileged access to Azure Tenancy (Required: azurehound)
    """
    query = "MATCH p=(n {owned:true, enabled:true, domain: '%s'})-[r:MemberOf|AZGlobalAdmin|AZPrivilegedRoleAdmin*1..]->(:AZTenant) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_all_owned_users_where_group_grants_azure_privileged_access")
def find_all_owned_users_where_group_grants_azure_privileged_access(domain):
    """
    Owned: [WIP] Find all owned user where group membership grants privileged access to Azure Tenancy (Required: azurehound)
    """
    query = "MATCH p=(n {owned:true, enabled:true, domain: '%s'})-[:MemberOf*1..]->(g:Group)-[r:AZGlobalAdmin|AZPrivilegedRoleAdmin*1..]->(:AZTenant) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_all_owners_of_azure_applications_with_dangerous_rights")
def find_all_owners_of_azure_applications_with_dangerous_rights(domain):
    """
    Owned: [WIP] Find all Owners of Azure Applications with Owners to Service Principals with Dangerous Rights (Required: azurehound)
    """
    query = "MATCH p = (n {enabled:true, owned:true, domain: '%s'})-[:AZOwns]->(azapp:AZApp)-[r1]->(azsp:AZServicePrincipal)-[r:AZGlobalAdmin|AZPrivilegedRoleAdmin*1..]->(azt:AZTenant) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_all_owned_groups_granting_network_share_access")
def find_all_owned_groups_granting_network_share_access(domain):
    """
    Find all owned groups that grant access to network shares
    """
    query = "MATCH p=(u:User {owned:true, domain: '%s'})-[:MemberOf*1..]->(g:Group) where (any(prop in keys(g) where g[prop] contains '\\\\')) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_all_sessions_to_computers_without_laps")
def route_all_sessions_to_computers_without_laps(domain):
    """
    Route all sessions to computers WITHOUT LAPS (Required: sessions)
    """
    query = "MATCH p=(u:User {owned:true, domain: '%s'})<-[r:HasSession]-(c:Computer {haslaps:false}) RETURN p ORDER BY c.name" % domain
    return run_query(query)

@mcp.tool("tool://route_all_sessions_to_computers")
def route_all_sessions_to_computers(domain):
    """
    Route all sessions to computers (Required: sessions)
    """
    query = "MATCH p=(u:User {owned:true, domain: '%s'})<-[r:HasSession]-(c:Computer) RETURN p ORDER BY c.name" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_non_privileged_users_with_local_admin")
def list_enabled_non_privileged_users_with_local_admin(domain):
    """
    List enabled non-privileged user(s) with \"Local Admin\" permission
    """
    query = "MATCH p=(u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|AdminTo*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_non_privileged_users_with_local_admin_and_sessions")
def list_enabled_non_privileged_users_with_local_admin_and_sessions(domain):
    """
    List enabled non-privileged user(s) with \"Local Admin\" permission, and any active sessions and their group membership(s)
    """
    query = "MATCH p=(u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|AdminTo*1..]->(c:Computer) OPTIONAL MATCH p2=(c)-[:HasSession]->(u2:User) OPTIONAL MATCH p3=(u2:User)-[:MemberOf*1..]->(:Group) RETURN p, p2, p3" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_non_privileged_users_with_rdp")
def list_enabled_non_privileged_users_with_rdp(domain):
    """
    List enabled non-privileged user(s) with \"RDP\" permission
    """
    query = "MATCH p=(u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|CanRDP*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_non_privileged_users_with_rdp_and_sessions")
def list_enabled_non_privileged_users_with_rdp_and_sessions(domain):
    """
    List enabled non-privileged user(s) with \"RDP\" permission, and any active sessions and their group membership(s)
    """
    query = "MATCH p=(u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|CanRDP*1..]->(c:Computer) OPTIONAL MATCH p2=(c)-[:HasSession]->(u2:User) OPTIONAL MATCH p3=(u2:User)-[:MemberOf*1..]->(:Group) RETURN p, p2, p3" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_non_privileged_users_with_sqladmin")
def list_enabled_non_privileged_users_with_sqladmin(domain):
    """
    List enabled non-privileged user(s) with \"SQLAdmin\" permission
    """
    query = "MATCH p=(u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|SQLAdmin*1..]->(c:Computer) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_domain_users_group_memberships")
def list_all_domain_users_group_memberships(domain):
    """
    List all \"Domain Users\" group membership(s)
    """
    query = "MATCH p=(g1:Group {domain: '%s'})-[:MemberOf*1..]->(g2:Group) WHERE g1.name STARTS WITH 'DOMAIN USERS' RETURN p ORDER BY g2.name" % domain
    return run_query(query)

@mcp.tool("tool://list_all_authenticated_users_group_memberships")
def list_all_authenticated_users_group_memberships(domain):
    """
    List all \"Authenticated Users\" group membership(s)
    """
    query = "MATCH p=(g1:Group {domain: '%s'})-[:MemberOf*1..]->(g2:Group) WHERE g1.name STARTS WITH 'AUTHENTICATED USERS' RETURN p ORDER BY g2.name" % domain
    return run_query(query)

@mcp.tool("tool://find_all_enabled_as_rep_roastable_users")
def find_all_enabled_as_rep_roastable_users(domain):
    """
    Find all enabled AS-REP roastable user(s)
    """
    query = "MATCH (u:User {dontreqpreauth: true, enabled:true, domain: '%s'}) WHERE NOT u.name CONTAINS '$' and NOT u.name CONTAINS 'KRBTGT' RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://find_all_enabled_kerberoastable_users")
def find_all_enabled_kerberoastable_users(domain):
    """
    Find all enabled kerberoastable user(s)
    """
    query = "MATCH (u:User {hasspn: true, enabled:true, domain: '%s'}) WHERE NOT u.name CONTAINS '$' and NOT u.name CONTAINS 'KRBTGT' RETURN u" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_rights_to_users")
def route_non_privileged_users_with_dangerous_rights_to_users(domain):
    """
    Route non-privileged user(s) with dangerous rights to user(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:User)) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_rights_to_groups")
def route_non_privileged_users_with_dangerous_rights_to_groups(domain):
    """
    Route non-privileged user(s) with dangerous rights to group(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:Group)) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_rights_to_computers")
def route_non_privileged_users_with_dangerous_rights_to_computers(domain):
    """
    Route non-privileged user(s) with dangerous rights to computer(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:Computer)) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_rights_to_gpos")
def route_non_privileged_users_with_dangerous_rights_to_gpos(domain):
    """
    Route non-privileged user(s) with dangerous rights to GPO(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:GPO)) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_users_with_dangerous_rights_to_privileged_nodes")
def route_non_privileged_users_with_dangerous_rights_to_privileged_nodes(domain):
    """
    Route non-privileged user(s) with dangerous rights to privileged node(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((u:User {enabled: true, admincount: false, domain: '%s'})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a {admincount: true})) WHERE NOT u = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_computers_with_dangerous_rights_to_users")
def route_non_privileged_computers_with_dangerous_rights_to_users(domain):
    """
    Route non-privileged computer(s) with dangerous rights to user(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((c:Computer {admincount: false})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:User {domain: '%s'})) WHERE NOT c = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_computers_with_dangerous_rights_to_groups")
def route_non_privileged_computers_with_dangerous_rights_to_groups(domain):
    """
    Route non-privileged computer(s) with dangerous rights to group(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((c:Computer {admincount: false})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:Group {domain: '%s'})) WHERE NOT c = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_computers_with_dangerous_rights_to_computers")
def route_non_privileged_computers_with_dangerous_rights_to_computers(domain):
    """
    Route non-privileged computer(s) with dangerous rights to computer(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((c:Computer {admincount: false})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:Computer {domain: '%s'})) WHERE NOT c = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_computers_with_dangerous_rights_to_gpos")
def route_non_privileged_computers_with_dangerous_rights_to_gpos(domain):
    """
    Route non-privileged computer(s) with dangerous rights to GPO(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((c:Computer {admincount: false})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a:GPO {domain: '%s'})) WHERE NOT c = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_non_privileged_computers_with_dangerous_rights_to_privileged_nodes")
def route_non_privileged_computers_with_dangerous_rights_to_privileged_nodes(domain):
    """
    Route non-privileged computer(s) with dangerous rights to privileged node(s) [HIGH RAM]
    """
    query = "MATCH p=allshortestpaths((c:Computer {admincount: false})-[:MemberOf|Owns|WriteDacl|GenericAll|WriteOwner|ExecuteDCOM|AllowedToDelegate|ForceChangePassword|AdminTo*1..]->(a {admincount: true, domain: '%s'})) WHERE NOT c = a RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_esc1_vulnerable_certificate_templates")
def list_esc1_vulnerable_certificate_templates(domain):
    """
    List ESC1 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {Enabled:true, type:'Certificate Template', `Enrollee Supplies Subject`:true, `Client Authentication`:true, domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_esc2_vulnerable_certificate_templates")
def list_esc2_vulnerable_certificate_templates(domain):
    """
    List ESC2 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {Enabled:true, type:'Certificate Template', domain: '%s'}) WHERE (n.`Extended Key Usage` = [] or 'Any Purpose' IN n.`Extended Key Usage`) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_esc3_vulnerable_certificate_templates")
def list_esc3_vulnerable_certificate_templates(domain):
    """
    List ESC3 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {Enabled:true, type:'Certificate Template', domain: '%s'}) WHERE (n.`Extended Key Usage` = [] or 'Any Purpose' IN n.`Extended Key Usage` or 'Certificate Request Agent' IN n.`Extended Key Usage`) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_esc4_vulnerable_certificate_templates")
def list_esc4_vulnerable_certificate_templates(domain):
    """
    List ESC4 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH p=shortestPath((g)-[:GenericAll|GenericWrite|Owns|WriteDacl|WriteOwner*1..]->(n:GPO {Enabled:true, type:'Certificate Template', domain: '%s'})) WHERE g<>n RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_esc6_vulnerable_certificate_templates")
def list_esc6_vulnerable_certificate_templates(domain):
    """
    List ESC6 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {type:'Enrollment Service', `User Specified SAN`:'Enabled', domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_esc7_vulnerable_certificate_templates")
def list_esc7_vulnerable_certificate_templates(domain):
    """
    List ESC7 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH p=shortestPath((g)-[r:GenericAll|GenericWrite|Owns|WriteDacl|WriteOwner|ManageCa|ManageCertificates*1..]->(n:GPO {type:'Enrollment Service', domain: '%s'})) WHERE g<>n RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_esc8_vulnerable_certificate_templates")
def list_esc8_vulnerable_certificate_templates(domain):
    """
    List ESC8 vulnerable Certificate Template(s) [Required: Certipy]
    """
    query = "MATCH (n:GPO {type:'Enrollment Service', `Web Enrollment`:'Enabled', domain: '%s'}) RETURN n" % domain
    return run_query(query)

@mcp.tool("tool://list_all_cross_domain_user_sessions_and_memberships")
def list_all_cross_domain_user_sessions_and_memberships(domain):
    """
    List all cross-domain user session(s) and user group membership(s)
    """
    query = "MATCH p=(g1:Group)<-[:MemberOf*1..]-(u:User {enabled:true, domain: '%s'})<-[:HasSession]-(c:Computer) WHERE NOT u.domain = c.domain RETURN p ORDER BY c.name" % domain
    return run_query(query)

@mcp.tool("tool://list_privileged_users_without_protected_users")
def list_privileged_users_without_protected_users(domain):
    """
    List privileged user(s) without \"Protected Users\" group membership
    """
    query = "MATCH (u:User {admincount:true, domain: '%s'}), (c:Computer), (u)-[:MemberOf*1..]->(g) WHERE g.name CONTAINS 'Protected Users' WITH COLLECT(u) AS privilegedUsers MATCH (u2:User {admincount:true}) WHERE NOT u2 IN privilegedUsers RETURN u2" % domain
    return run_query(query)

@mcp.tool("tool://list_custom_privileged_groups")
def list_custom_privileged_groups(domain):
    """
    List custom privileged group(s)
    """
    query = "MATCH (g:Group {admincount:true, highvalue:false, domain: '%s'}) WHERE NOT (g.objectid =~ '(?i)S-1-5-.*-512' or g.objectid =~ '(?i)S-1-5-.*-519' or g.objectid =~ '(?i)S-1-5-.*-544' or g.objectid =~ '(?i)S-1-5-.*-548' or g.objectid CONTAINS '-552' or g.objectid =~ '(?i)S-1-5-.*-526' or g.objectid =~ '(?i)S-1-5-.*-521' or g.objectid =~ '(?i)S-1-5-.*-527' or g.objectid =~ '(?i)S-1-5-.*-518') RETURN g" % domain
    return run_query(query)

@mcp.tool("tool://list_enabled_svc_accounts_with_privileged_group_memberships")
def list_enabled_svc_accounts_with_privileged_group_memberships(domain):
    """
    List all enabled SVC account(s) with privileged group membership(s)
    """
    query = "MATCH p=(u:User {enabled: true, hasspn: true, domain: '%s'})-[:MemberOf*1..]->(g:Group {admincount: true}) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://route_privileged_users_with_sessions_to_non_privileged_computers")
def route_privileged_users_with_sessions_to_non_privileged_computers(domain):
    """
    Route all privileged user(s) with sessions to non-privileged computer(s) [Required: sessions]
    """
    query = "MATCH (c:Computer), (u:User), (g:Group), (c)-[:MemberOf*1..]->(:Group {admincount:false}) MATCH p=(c)-[:HasSession]->(u {admincount:true, domain: '%s'}) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_allshortestpaths_with_dangerous_rights_to_adminsdholder")
def find_allshortestpaths_with_dangerous_rights_to_adminsdholder(domain):
    """
    Find allshortestpaths with dangerous rights to AdminSDHolder object
    """
    query = "MATCH p=allshortestpaths((u:User {enabled:true, admincount:false, domain: '%s'})-[*]->(c:Container)) WHERE c.distinguishedname CONTAINS 'ADMINSDHOLDER' RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_allshortestpaths_with_dcsync_to_domain")
def find_allshortestpaths_with_dcsync_to_domain(domain):
    """
    Find allshortestpaths with DCSync to domain object
    """
    query = "MATCH p=allshortestpaths((u:User {enabled:true, admincount:false, domain: '%s'})-[r:MemberOf|DCSync*1..]->(:Domain)) RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://find_allshortestpaths_with_shadow_credential_permission")
def find_allshortestpaths_with_shadow_credential_permission(domain):
    """
    Find allshortestpaths with Shadow Credential permission to principal(s)
    """
    query = "MATCH p=allshortestpaths((a {domain: '%s'})-[:MemberOf|AddKeyCredentialLink*1..]->(b)) WHERE NOT a=b RETURN p" % domain
    return run_query(query)

@mcp.tool("tool://list_all_tenancy")
def list_all_tenancy():
    """
    List all Tenancy (Required: azurehound)
    """
    query = "MATCH (t:AZTenant) RETURN t"
    return run_query(query)

@mcp.tool("tool://list_all_aad_groups_synchronized_with_ad")
def list_all_aad_groups_synchronized_with_ad():
    """
    [WIP] List all AAD Group(s) that are synchronized with AD (Required: azurehound)
    """
    query = "MATCH (n:Group) WHERE n.objectid CONTAINS 'S-1-5' AND n.azsyncid IS NOT NULL RETURN n"
    return run_query(query)

@mcp.tool("tool://list_all_principals_used_for_syncing_ad_and_aad")
def list_all_principals_used_for_syncing_ad_and_aad():
    """
    [WIP] List all principal(s) used for syncing AD and AAD
    """
    query = "MATCH (u) WHERE (u:User OR u:AZUser) AND (u.name =~ '(?i)^MSOL_|.*AADConnect.*' OR u.userprincipalname =~ '(?i)^sync_.*') OPTIONAL MATCH (u)-[:HasSession]->(s:Session) RETURN u, s"
    return run_query(query)

@mcp.tool("tool://list_all_enabled_azure_users")
def list_all_enabled_azure_users():
    """
    List all enabled Azure User(s) (Required: azurehound)
    """
    query = "MATCH (u:AZUser {enabled:true}) RETURN u"
    return run_query(query)

@mcp.tool("tool://list_all_enabled_azure_users_group_memberships")
def list_all_enabled_azure_users_group_memberships():
    """
    List all enabled Azure User(s) Azure Group membership(s) (Required: azurehound)
    """
    query = "MATCH p=(azu:AZUser {enabled:true})-[:MemberOf*1..]->(azg:AZGroup) RETURN p"
    return run_query(query)

@mcp.tool("tool://list_all_ad_principals_with_edges_to_azure_principals")
def list_all_ad_principals_with_edges_to_azure_principals():
    """
    [WIP] List all AD principal(s) with edge(s) to Azure principal(s) (Required: azurehound)
    """
    query = "MATCH p=(u:User)-[r:MemberOf|AZResetPassword|AZOwns|AZUserAccessAdministrator|AZContributor|AZAddMembers|AZGlobalAdmin|AZVMContributor|AZOwnsAZAvereContributor*1..]->(n) WHERE u.objectid CONTAINS 'S-1-5-21' RETURN p"
    return run_query(query)

@mcp.tool("tool://list_all_principals_with_privileged_access_to_azure_tenancy")
def list_all_principals_with_privileged_access_to_azure_tenancy():
    """
    [WIP] List all principal(s) with privileged access to Azure Tenancy (Required: azurehound)
    """
    query = "MATCH (a) WHERE (a:User OR a:AZUser) WITH a MATCH p=(a)-[r:MemberOf|AZGlobalAdmin|AZPrivilegedRoleAdmin*1..]->(azt:AZTenant) RETURN p"
    return run_query(query)

@mcp.tool("tool://route_principals_to_azure_applications_and_service_principals")
def route_principals_to_azure_applications_and_service_principals():
    """
    [WIP] Route all principal(s) that have control permissions to Azure Application(s) running as Azure Service Principals (AzSP), and route from privileged ASP to Azure Tenancy (Required: azurehound)
    """
    query = "MATCH (a) WHERE (a:User OR a:AZUser) WITH a MATCH p=(a)-[:MemberOf|AZOwns|AZAppAdmin*1..]->(azapp:AZApp) OPTIONAL MATCH p2=(azapp)-[:AZRunsAs]->(azsp:AZServicePrincipal) OPTIONAL MATCH p3=(azsp)-[:MemberOf|AZGlobalAdmin|AZPrivilegedRoleAdmin*1..]->(azt:AZTenant) RETURN p, p2, p3"
    return run_query(query)

@mcp.tool("tool://route_user_principals_to_azure_service_principals")
def route_user_principals_to_azure_service_principals():
    """
    [WIP] Route all user principal(s) that have control permissions to Azure Service Principals (AzSP), and route from AzSP to principal(s) (Required: azurehound)
    """
    query = "MATCH (a) WHERE (a:User OR a:AZUser) WITH a MATCH p=allShortestPaths((a)-[*]->(azsp:AZServicePrincipal)-[*]->(b)) WHERE NOT a=b RETURN p"
    return run_query(query)

@mcp.tool("tool://route_azure_users_with_dangerous_rights_to_users")
def route_azure_users_with_dangerous_rights_to_users():
    """
    [WIP] Route from Azure User principal(s) that have dangerous rights to Azure User and User principal(s) (Required: azurehound)
    """
    query = "MATCH (a) WHERE (a:User OR a:AZUser) WITH a MATCH p=allShortestPaths((u:AZUser)-[*]->(a)) WHERE NOT a=u RETURN p"
    return run_query(query)

@mcp.tool("tool://route_principals_to_azure_vm")
def route_principals_to_azure_vm():
    """
    [WIP] Route from principal(s) to Azure VM (Required: azurehound)
    """
    query = "MATCH p=allshortestpaths((a)-[*]->(vm:AZVM)) WHERE NOT a=vm RETURN p"
    return run_query(query)

@mcp.tool("tool://route_principals_to_global_administrators")
def route_principals_to_global_administrators():
    """
    [WIP] Route from principal(s) to principal(s) with Global Administrator permissions (Required: azurehound)
    """
    query = "MATCH p=(ga)-[:AZGlobalAdmin|AZPrivilegedAdminRole*1..]->(:AZTenant) WHERE (ga:User OR ga:AZUser) WITH ga MATCH p=allshortestpaths((a)-[*]->(ga)) WHERE NOT a=ga RETURN p"
    return run_query(query)



if __name__ == '__main__':
    try:
        mcp.run(transport='stdio')
    except Exception as e:
        print(f"啟動 MCP 服務器時發生錯誤: {e}")