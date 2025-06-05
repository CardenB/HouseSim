# House Simulator

A Streamlit-based web application for simulating mortgage scenarios and analyzing housing costs.

The application is hosted at: https://housesim.cardieb.com

## Local Development Setup

### Running without Docker

1. Create and activate a virtual environment (optional but recommended):
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Run the application:
```bash
streamlit run house_sim.py --server.port 3001
```

The application will be available at http://localhost:3001

## Quick Start with Docker

### Running the Container

To start the application for the first time:

```bash
# Build the Docker image
docker build -t house-sim .

# Run the container
docker run -d --name house-sim -p 3001:3001 house-sim
```

The application will be available at http://localhost:3001

### Managing the Container

Stop the container:
```bash
docker stop house-sim
```

Start an existing container:
```bash
docker start house-sim
```

Remove the container (if you need to recreate it):
```bash
docker stop house-sim
docker rm house-sim
```

## Development and Redeployment

When you make changes to the code, you'll need to rebuild and redeploy the container:

1. Stop and remove the existing container:
```bash
docker stop house-sim && docker rm house-sim
```

2. Rebuild the image with your changes:
```bash
docker build -t house-sim .
```

3. Start a new container:
```bash
docker run -d --name house-sim -p 3001:3001 house-sim
```

## Application Settings

The application runs on port 3001 by default. This is configured in both:
- The Streamlit configuration (in the Dockerfile)
- The container port mapping (-p 3001:3001)

If you need to use a different port:
1. Update the port in the Dockerfile's Streamlit configuration
2. Change the port mapping when running the container
3. Rebuild and redeploy using the steps above

## Deployment

The application is automatically deployed to https://housesim.cardieb.com

## Troubleshooting

### Viewing Logs

To view the container's logs:
```bash
# View logs
docker logs house-sim

# Follow logs in real-time
docker logs -f house-sim
```

If the application isn't accessible, check:
1. Container status: `docker ps -a`
2. Container logs for errors: `docker logs house-sim`
3. Port availability: `netstat -tuln | grep 3001`

## Input Parameters

### Mortgage Details
- **Purchase price**: The total cost of the home
- **Down payment**: Initial payment made on the home
- **Interest rate**: Annual interest rate for the mortgage
- **Term**: Length of the mortgage in years
- **Property tax**: Can be entered as either:
  - Annual percentage of home value
  - Monthly fixed amount
- **Property tax appreciation**: Annual percentage increase in property taxes
- **Insurance**: Monthly insurance payment

### Recast Strategy
- **Method**: Choose between:
  - **Savings-based**: Automatically recast when savings exceed buffer
  - **Fixed lump sum**: Recast with fixed amount at regular intervals
- **Months between recasts**: How often to attempt recasting
- **Initial cash**: Starting savings amount
- **Monthly savings**: (Savings-based only) Monthly amount added to savings
- **Cash buffer**: (Savings-based only) Minimum savings to maintain
- **Recast amount**: (Fixed lump sum only) Amount to recast each interval

### Income Scenarios (Optional)
- **Primary Income**:
  - Gross annual income
  - Option to manually set tax rate or use calculated rate
- **Secondary Income**:
  - Gross annual income
  - Option to manually set tax rate or use calculated rate
- **Baseline non-housing spend**: Monthly non-housing expenses

### Chart Settings
- **Time horizon**: Number of months to display in charts

## Charts and Visualizations

The application provides several visualizations:
1. **Monthly Payment**: Shows payment amount over time with recast points marked
2. **Cumulative Payments**: Compares total payments with and without recasting
3. **Payment vs. Income Ratios**: (If income entered) Shows PITI ratios for pre and post-tax income
4. **Savings Balance**: Tracks savings account balance over time