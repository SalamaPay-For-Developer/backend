# SalamaPay Backend

One Wallet. One Card. One Platform. Pay Everything.

## Setup Instructions

1.  **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```
2.  **Activate the virtual environment:**
    -   Windows: `venv\Scripts\activate`
    -   macOS/Linux: `source venv/bin/activate`
3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```
4.  **Run migrations:**
    ```bash
    python manage.py migrate
    ```
5.  **Start the development server:**
    ```bash
    python manage.py runserver
    ```

## Project Structure

- `backend/`: Core project settings.
- `core/`: Common functionalities and shared models.
- `requirements.txt`: Python dependencies.
