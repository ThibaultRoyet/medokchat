from dotenv import load_dotenv
load_dotenv()

from ui import demo

if __name__ == "__main__":
    demo.launch(server_port=7860)
