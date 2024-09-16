# README

Welcome to the `wennwo` project!

## Overview

This project contains multiple `.py` files that are used for the website. Each file serves a specific purpose and contributes to the functionality of the website.

## File Descriptions

Here is a brief description of each `.py` file:

1. `__init__.py`: This is the main entry point of the website. It handles the routing and serves as the starting point for the application.

2. `functions.py`: This file contains utility functions that are used throughout the website. It includes functions for handling database connections, file operations, and other common tasks.

3. `models.py`: This file defines the data models used in the website. It includes classes for representing users, surveys, comments, and other entities.

4. `views.py`: This file contains the view functions that handle HTTP requests and generate the corresponding responses. It includes functions for rendering templates, processing form data, and interacting with the database.

5. `auth.py`: This file stores the views related to the authentification like sign in oder sign out.

6. `forms.py`: This file contains the forms used in the website. The forms are then used inside the auth.py and views.py.

7. `api.py`: This file contains the requests for the API that are reachable under /api.

Please refer to the individual files for more detailed information about their contents and functionalities.

## Getting Started

To get started with the website, follow these steps:

1. Clone the repository to your local machine.
2. Install the required dependencies by running `pip install -r requirements.txt`.
3. Setup the database and implement a login
4. Run the `app.py` file to start the website.