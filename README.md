# BloodHound MCP
BloodHound MCP (Model Context Protocol) is an innovative extension of the BloodHound tool, designed to enable Large Language Models (LLMs) to interact with and analyze Active Directory (AD) and Azure Active Directory (AAD) environments through natural language queries. By leveraging the power of LLMs, BloodHound MCP allows users to perform complex queries and retrieve insights from their AD/AAD environments using simple, conversational commands.

## Features
- **Natural Language Queries**: Use conversational language to query your AD/AAD environment without needing to write Cypher queries manually.
- **LLM-Powered Analysis**: Harness the capabilities of Large Language Models to interpret and execute queries on your behalf.
- **Seamless Integration**: Works with existing BloodHound data stored in Neo4j, providing a user-friendly interface for complex analysis.
- **Customizable**: Easily configure the system to work with your specific environment and tools.

## Configure the MCP Server
```json
{
  "mcpServers": {
    "BloodHound": {
      "name": "BloodHound",
      "isActive": true,
      "command": "uv",
      "args": [
        "run",
        "--with",
        "mcp[cli],neo4j",
        "mcp",
        "run",
        "<PATH_TO_THE_PROJECT>server.py"
      ],
      "env": {
        "BLOODHOUND_URI": "bolt://localhost:7687",
        "BLOODHOUND_USERNAME": "neo4j",
        "BLOODHOUND_PASSWORD": "bloodhound"
      }
    }
  }
}
```


## Usage
![](img/1.png)
![](img/2.png)
![](img/3.png)

## Configuration
To customize BloodHound MCP, update the configuration file in your MCP-supported tool. Key settings include:

- Neo4j Database Connection:
    - `BLOODHOUND_URI`: The URI of your Neo4j database (e.g., bolt://localhost:7687).
    - `BLOODHOUND_USERNAME`: Your Neo4j username.
    - `BLOODHOUND_PASSWORD`: Your Neo4j password.
- Server Settings: Adjust the command and args to match your environment and tool requirements.

## Contributing
We welcome contributions to BloodHound MCP! To get involved:

1. Fork the Repository: Create your own copy on GitHub.
2. Create a Branch: Work on your feature or fix in a new branch.
3. Submit a Pull Request: Include a clear description of your changes.


## Special Thanks
Custom queries from : https://github.com/CompassSecurity/BloodHoundQueries