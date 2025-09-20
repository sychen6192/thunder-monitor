import yaml

def load_config(env="PROD"):
    with open("config.yaml", "r") as f:
        config = yaml.safe_load(f)
        return config[env]
