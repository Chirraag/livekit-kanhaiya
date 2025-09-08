# LiveKit Agent Configuration System

This project provides a configurable LiveKit agent with a web-based configuration interface. The system allows you to customize the agent's personality, begin message, and available tools through a beautiful React interface that stores configurations in Firebase.

## Project Structure

```
/Users/kanhaiyamohan/Desktop/livekit/          # Main agent project
├── agents.py                                   # LiveKit agent implementation
├── config_loader.py                          # Firebase configuration loader
├── tools.py                                   # Dynamic tools implementation
├── prompts.py                                 # Original prompts (legacy)
├── requirements.txt                           # Python dependencies
└── calldash-51b0f-firebase-adminsdk-fbsvc-d6f01c4342.json  # Firebase credentials

/Users/kanhaiyamohan/Desktop/livekit-config/   # Configuration UI
├── src/
│   ├── App.tsx                               # Main React application
│   ├── firebase.ts                          # Firebase configuration
│   ├── types.ts                             # TypeScript interfaces
│   └── firebase-credentials.json            # Firebase credentials
├── package.json                              # Node.js dependencies
└── tailwind.config.js                       # Tailwind CSS configuration
```

## Features

### Configuration Interface
- **Agent Personality**: Configure the agent's instructions and behavior
- **Begin Message**: Customize the first message the agent says
- **Dynamic Tools**: Create and configure REST API tools with parameters
- **Built-in Search**: Always includes web search functionality
- **Real-time Validation**: Validates tool names and configurations
- **Firebase Storage**: Automatically saves and loads configurations

### Agent Features
- **Dynamic Configuration Loading**: Reads configuration from Firebase on startup
- **Custom Tools**: Dynamically creates tools based on saved configurations
- **Fallback Support**: Uses default configuration if Firebase is unavailable
- **Error Handling**: Comprehensive error handling and logging

## Setup Instructions

### 1. Install Dependencies

For the main agent:
```bash
cd /Users/kanhaiyamohan/Desktop/livekit
pip install -r requirements.txt
pip install firebase-admin
```

For the configuration UI:
```bash
cd /Users/kanhaiyamohan/Desktop/livekit-config
npm install
```

### 2. Firebase Setup
- Your Firebase credentials are already configured
- The system uses Firestore database with collection `configurations`
- Configuration document ID: `current`

### 3. Run the Configuration UI

```bash
cd /Users/kanhaiyamohan/Desktop/livekit-config
npm start
```

Access the configuration interface at: http://localhost:3000

### 4. Run the LiveKit Agent

```bash
cd /Users/kanhaiyamohan/Desktop/livekit
python agents.py
```

## Using the Configuration Interface

### Agent Configuration
1. **Agent Instruction**: Define the agent's personality and behavior
2. **Begin Message**: Set the greeting message the agent will use

### Tool Configuration
1. Click "Add Tool" to create a new REST API tool
2. Configure:
   - **Tool Name**: Must be lowercase with underscores only (e.g., `get_weather`)
   - **Description**: What the tool does
   - **Request Type**: GET, POST, PUT, or DELETE
   - **Request URL**: The API endpoint
   - **Parameters**: Define parameter name, type (string/number/boolean), defaults, and required status

3. Click "Save Configuration" to store in Firebase

### Built-in Tools
- **search_web**: Always available for web searches using DuckDuckGo
- Cannot be deleted or modified (protected)

## How It Works

### Configuration Flow
1. User configures agent through React interface
2. Configuration saved to Firebase Firestore
3. Agent loads configuration on startup from Firebase
4. Agent creates dynamic tools based on configuration
5. Agent uses configured personality and begin message

### Dynamic Tool Creation
- Tools are created at runtime based on Firebase configuration
- Each tool becomes a LiveKit function_tool
- HTTP requests are made according to tool configuration
- Responses are returned to the agent for processing

### Error Handling
- Firebase connection failures fall back to default configuration
- Invalid tool configurations are logged and skipped
- HTTP errors in tools are gracefully handled and reported

## Configuration Schema

```typescript
interface AgentConfiguration {
  agentInstruction: string;    // Agent personality
  beginMessage: string;        // First message
  tools: Tool[];              // Array of tool configurations
  updatedAt: Date;            // Last update timestamp
}

interface Tool {
  id: string;                 // Unique identifier
  name: string;               // Function name (lowercase, underscores)
  description: string;        // Tool description
  requestType: 'GET'|'POST'|'PUT'|'DELETE';
  requestUrl: string;         // API endpoint
  parameters: ToolParameter[]; // Parameter definitions
  enabled: boolean;           // Whether tool is active
}

interface ToolParameter {
  name: string;               // Parameter name
  type: 'string'|'number'|'boolean';
  required: boolean;          // Is parameter required
  defaultValue?: string;      // Default value if not provided
  description?: string;       // Parameter description
}
```

## Development Notes

- Configuration changes take effect on next agent restart
- Firebase credentials are included in both projects
- The system is designed for local development (no authentication required)
- All tool names must follow Python function naming conventions
- The search_web tool is always included and cannot be removed

## Troubleshooting

### Common Issues
1. **Firebase Connection Failed**: Check credentials file path and Firebase project settings
2. **Tool Validation Failed**: Ensure tool names follow naming conventions
3. **Agent Startup Failed**: Check that all required dependencies are installed

### Logs
- Agent logs appear in console when running `python agents.py`
- Configuration UI logs appear in browser developer console
- Firebase operations are logged for debugging