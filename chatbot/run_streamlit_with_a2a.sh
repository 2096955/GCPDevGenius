#!/bin/bash

# Set environment variables
export GOOGLE_API_KEY=$(grep GOOGLE_API_KEY .env | cut -d '=' -f2)
export HOST_AGENT_URL="http://localhost:8000"
export CODE_AGENT_URL="http://localhost:8001"
export DATA_AGENT_URL="http://localhost:8002"

# Start the A2A agents in background
echo "Starting A2A agents..."

# Start the Host Agent
echo "Starting Host Agent on port 8000..."
cd chatbot
python -m a2a.run_agents --host-port 8000 --code-port 8001 --data-port 8002 &
HOST_PID=$!

# Give agents time to start up
echo "Waiting for agents to start..."
sleep 5

# Check if agents are running
if ps -p $HOST_PID > /dev/null; then
    echo "A2A agents are running successfully!"
else
    echo "Warning: A2A agents failed to start. The Streamlit app will use Vertex AI only."
fi

# Start the Streamlit app
echo "Starting Streamlit app..."
cd ..
streamlit run chatbot/agent.py 