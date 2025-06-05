FROM python:3.12-slim

WORKDIR /app

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create Streamlit config directory and configuration
RUN mkdir -p /root/.streamlit
RUN echo '\
[server]\n\
address = "0.0.0.0"\n\
port = 3001\n\
enableCORS = false\n\
enableXsrfProtection = false\n\
' > /root/.streamlit/config.toml

# Expose the configured port
EXPOSE 3001

# Start streamlit
CMD ["streamlit", "run", "house_sim.py", "--server.address", "0.0.0.0", "--server.port", "3001"]