# 4353Fall24
Raj Singh's COSC 4353: Software Design, Fall 2024

Group Members:
[Zachary Clark]
[Andy Torres]
[Eraj Anwar]
[Cholponai Osmonkulova]


4353Fall24 Flask Project

Prerequisites:
Ensure you have the following installed:

	Python 3:
		-https://www.python.org/downloads/

	Git:
		-https://git-scm.com/downloads

Installation Instructions:

	Step 1: Clone the Repository
		
		Visit this link:

			https://github.com/zzclark17/4353Fall24.git


		Or run the following command on a terminal to clone the repository:

			git clone https://github.com/zzclark17/4353Fall24.git


		Go into the project directory:

			cd 4353Fall24


	Step 2: Set Up a Virtual Environment

		Create a virtual environment using Python:


			python -m venv venv


	Step 3: Activate the Virtual Environment

		Windows (PowerShell):

  			.\venv\Scripts\Activate.ps1
  

		Windows (Command Prompt):

  			.\venv\Scripts\activate


		macOS/Linux:
  
  			source venv/bin/activate
  
		
	Step 4: Install Dependencies

		Once the virtual environment is activated, install the necessary dependencies:


			pip install -r requirements.txt




Running the Project

	Step 1: Set Environment Variables

		Before running the project, set the necessary environment variables:

		Windows (PowerShell):

  			$env:FLASK_APP = "server.py"
  			$env:FLASK_ENV = "development"
  

		Windows (Command Prompt):
  
  			set FLASK_APP=server.py
  			set FLASK_ENV=development
  

		macOS/Linux:
  
  			export FLASK_APP="server.py"
  			export FLASK_ENV="development"
 

	Step 2: Run the Flask Server

	Now you can start the Flask server:


		flask run


Once the server is running, hold CTRL and press on http://127.0.0.1:5000 from within the terminal. 

In order to run the Unit Tests Open test/test_flask_app.py and use the following command in the Terminal:

	python -m pytest --cov=server tests/

	*If you encounter test errors after running the command above more than once, it is because data was deleted from the database and the unit test failed to find the data because not it is missing. Ensure to revert the database back to its original state by discarding any changes that were made. 