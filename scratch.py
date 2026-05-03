import os
import json
from dotenv import load_dotenv
from forgeai.config.config_manager import ConfigManager
from forgeai.core.orchestrator import Orchestrator

load_dotenv()

def test_run():
    # Setup config
    ConfigManager.reset()
    cfg = ConfigManager.get_instance()
    cfg.config.workflow.auto_approve_checkpoints = True
    cfg.config.output.project_dir = "./generated_project"
    cfg.config.output.enable_git = False
    cfg.config.web_dashboard.enabled = False
    cfg.config.llm.api_key_env = "GOOGLE_API_KEY"
    cfg.config.docker.enabled = True
    
    # Initialize orchestrator
    orchestrator = Orchestrator(cfg)
    
    # Print callbacks
    def log(entry):
        print(f"[LOG] {entry.level}: {entry.message}")
        
    orchestrator.logger.add_listener(log)
    
    prompt = "Build a REST API for a simple Todo app with endpoints to create, read, update, and delete tasks. Each task has a title, description, and completion status. Use FastAPI and SQLite."
    
    print("Starting pipeline...")
    summary = orchestrator.run(prompt)
    print("Pipeline finished.")
    print("Summary:", json.dumps(summary, indent=2))

if __name__ == "__main__":
    test_run()
