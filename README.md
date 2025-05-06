# extract-subtitle
A platform to extract subtitles from a audio/video files.

A web application that extracts subtitles from audio and video files using OpenAI's Whisper model. The application provides a user-friendly interface for uploading media files and generating accurate subtitles in multiple languages.

## Features

- User authentication (sign up, login, logout)
- Upload MP3 and MP4 files
- Extract subtitles using AI
- Support for multiple languages
- Modern, responsive UI with Tailwind CSS

## Prerequisites

- Python 3.11 (required)
- pip (Python package installer)

## Getting Started

1. Clone the repository:
```bash
git clone <repository-url>
cd extract-subtitle
```

2. Create and activate a virtual environment:
```bash
# Create virtual environment
python3.11 -m venv .venv

# Activate virtual environment
# On macOS/Linux:
source .venv/bin/activate.fish
# On Windows:
.venv\Scripts\activate
```

3. Install the required packages:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file in the root directory with the following content:
```
FLASK_APP=app
FLASK_ENV=development
SECRET_KEY=your-secret-key-here
DATABASE_URL=sqlite:///app.db
```

5. Initialize the database:
```bash
# The database will be automatically created when you run the application
```

6. Run the application:
```bash
python wsgi.py
```

The application will be available at `http://localhost:5000`

## Usage

1. Register a new account or log in with existing credentials
2. Navigate to the dashboard
3. Upload an MP3 or MP4 file
4. Select the target language for subtitles
5. Click "Extract Subtitles" to process the file
6. Download the generated SRT file

## Project Structure

```
app/
├── __init__.py          # Flask app initialization
├── models.py            # Database models
├── auth/               # Authentication blueprint
│   ├── forms.py        # Login/Registration forms
│   └── routes.py       # Auth routes
├── main/               # Main blueprint
│   └── routes.py       # Main routes
└── templates/          # HTML templates
    ├── base.html       # Base template
    ├── auth/           # Auth templates
    │   ├── login.html
    │   └── register.html
    └── main/           # Main templates
        ├── index.html
        └── dashboard.html
```

## Technologies Used

- Flask - Web framework
- SQLAlchemy - Database ORM
- Flask-Login - User authentication
- Flask-WTF - Form handling
- Tailwind CSS - Styling
- OpenAI Whisper - Subtitle extraction

## License

This project is licensed under the MIT License - see the LICENSE file for details.
