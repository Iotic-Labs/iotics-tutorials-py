from logging import config

from constants import LOGGING_CONFIGURATION
from data_processor import DataProcessor
from flask import Flask, render_template
from follower_connector import FollowerConnector

config.dictConfig(LOGGING_CONFIGURATION)

app = Flask(__name__)
data_processor = DataProcessor()
follower_connector = FollowerConnector(data_processor, app)


def main():
    follower_connector.start()


@app.route("/")
def index():
    sensors_info = follower_connector.get_sensors_info()
    return render_template("index.html", data=sensors_info)


if __name__ == "__main__":
    main()
