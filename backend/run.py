from src import create_app

# Create an application instance
app = create_app()

if __name__ == '__main__':
    app.run(debug=True)