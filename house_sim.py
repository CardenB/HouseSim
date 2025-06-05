import streamlit as st
import pandas as pd
import numpy as np
import altair as alt
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# ---------------- Helper Functions ----------------
def calculate_fica_tax_2025(income, filing_status="married"):
    """Calculate FICA (Social Security and Medicare) taxes"""
    ss_wage_limit = 167700  # 2025 Social Security wage base
    medicare_additional_threshold = 250000 if filing_status == "married" else 200000
    
    # Social Security (6.2% up to wage base limit)
    ss_tax = min(income, ss_wage_limit) * 0.062
    
    # Medicare (1.45% + 0.9% additional on high incomes)
    medicare_tax = income * 0.0145
    if income > medicare_additional_threshold:
        medicare_tax += (income - medicare_additional_threshold) * 0.009
    
    return ss_tax + medicare_tax

def calculate_federal_tax_2025(income, filing_status="married"):
    """Calculate federal tax for 2025 - married filing jointly"""
    if filing_status == "married":
        upper_rates = [
            (23850, 0.10),
            (96950, 0.12),
            (206700, 0.22),
            (394600, 0.24),
            (501050, 0.32),
            (751600, 0.35),
            (float('inf'), 0.37)
        ]
    else:  # single
        upper_rates = [
            (11925, 0.10),
            (48475, 0.12),
            (103350, 0.22),
            (197300, 0.24),
            (250525, 0.32),
            (626350, 0.35),
            (float('inf'), 0.37)
        ]
    brackets = []
    for i, rate in enumerate(upper_rates):
        if i == 0:
            brackets.append((0, rate[0], rate[1]))
        else:
            brackets.append((upper_rates[i-1][0], rate[0], rate[1]))
    
    tax = 0
    for i, (lower, upper, rate) in enumerate(brackets):
        if income > lower:
            taxable_amount = min(income - lower, upper - lower)
            tax += taxable_amount * rate
    
    return tax

def calculate_ca_tax_2025(income, filing_status="married"):
    """Calculate California state tax for 2025 - married filing jointly"""
    if filing_status == "married":
        upper_rates = [
            (20198, 0.01),
            (47884, 0.02),
            (75576, 0.04),
            (104910, 0.06),
            (132590, 0.08),
            (677278, 0.093),
            (812728, 0.103),
            (1354550, 0.113),
            (float('inf'), 0.123)
        ]
    else:  # single
        upper_rates = [
            (10099, 0.01),
            (23942, 0.02),
            (37788, 0.04),
            (52455, 0.06),
            (66295, 0.08),
            (338639, 0.093),
            (406364, 0.103),
            (677275, 0.113),
            (float('inf'), 0.123)
        ]
    brackets = []
    for i, rate in enumerate(upper_rates):
        if i == 0:
            brackets.append((0, rate[0], rate[1]))
        else:
            brackets.append((upper_rates[i-1][0], rate[0], rate[1]))
    
    tax = 0
    for i, (lower, upper, rate) in enumerate(brackets):
        if income > lower:
            taxable_amount = min(income - lower, upper - lower)
            tax += taxable_amount * rate
    
    return tax

def calculate_effective_tax_rate(income, filing_status="married"):
    """Calculate combined effective tax rate including federal, CA state, and FICA taxes"""
    federal_tax = calculate_federal_tax_2025(income, filing_status)
    ca_tax = calculate_ca_tax_2025(income, filing_status)
    fica_tax = calculate_fica_tax_2025(income, filing_status)
    total_tax = federal_tax + ca_tax + fica_tax
    return (total_tax / income) * 100 if income > 0 else 0

def payment(balance, months_left, r_monthly):
    return balance * r_monthly / (1 - (1 + r_monthly) ** -months_left)

def simulate(term_mo, r_mo, tax, ins):
    balance = loan
    p_i = payment(balance, term_mo, r_mo)
    savings = initial_cash  # Start with initial cash
    cum_paid = 0
    cum_recast = 0
    rows = []
    
    # Continue to term_mo even after loan is paid, for tax/insurance
    for m in range(1, term_mo + 1):
        # Calculate appreciated property tax for this month
        current_tax = tax * (1 + tax_appreciation/100) ** (m/12)
        
        # pay mortgage this month
        interest = balance * r_mo if balance > 0 else 0
        principal = p_i - interest if balance > 0 else 0
        if balance > 0:
            balance -= principal
        total_pmt = (p_i if balance > 0 else 0) + current_tax + ins
        
        # Calculate tax benefit for this month
        monthly_tax_benefit = 0
        if use_secondary == "Secondary Income" and gross_income2 > 0:
            monthly_tax_benefit = calculate_tax_benefit(interest * 12, current_tax, gross_income2) / 12
        elif gross_income > 0:
            monthly_tax_benefit = calculate_tax_benefit(interest * 12, current_tax, gross_income) / 12
        
        recast_amount = 0
        # handle savings / lump only if there's still a balance
        if balance > 0:
            savings += surplus  # Add monthly savings first
            if method == "Savings-based":
                if m % recast_int == 0:
                    extra = max(0, savings - buffer_cash)
                    if extra > 0:
                        recast_amount = min(extra, balance)  # Don't recast more than remaining balance
                        balance -= recast_amount
                        savings -= recast_amount
                        if balance <= 0:
                            p_i = 0
                        else:
                            p_i = payment(balance, term_mo - m, r_mo)
            else:  # fixed lump
                if m % recast_int == 0 and lump > 0 and savings >= lump:
                    recast_amount = min(lump, balance)  # Don't recast more than remaining balance
                    balance -= recast_amount
                    savings -= recast_amount
                    if balance <= 0:
                        p_i = 0
                    else:
                        p_i = payment(balance, term_mo - m, r_mo)

        cum_recast += recast_amount
        cum_paid += total_pmt  # Only include regular payment in cumulative
        
        rows.append({
            "Month": m,
            "P&I": p_i if balance > 0 else 0,
            "Tax": current_tax,
            "TotalPayment": total_pmt,
            "CumulativePaid": cum_paid + cum_recast,  # Add recast total to cumulative only when reporting
            "Balance": balance,
            "RecastAmount": recast_amount,
            "CumulativeRecast": cum_recast,
            "IsPaidOff": balance <= 0,
            "SavingsBalance": savings,
            "MonthlyInterest": interest,
            "MonthlyTaxBenefit": monthly_tax_benefit,
            "EffectivePayment": total_pmt - monthly_tax_benefit
        })

    return pd.DataFrame(rows)

def simulate_no_recast(term_mo, r_mo, tax, ins):
    balance = loan
    p_i = payment(balance, term_mo, r_mo)
    savings = initial_cash  # Start with initial cash
    rows = []
    cum_paid = 0
    
    for m in range(1, term_mo + 1):
        # Calculate appreciated property tax for this month
        current_tax = tax * (1 + tax_appreciation/100) ** (m/12)
        
        interest = balance * r_mo if balance > 0 else 0
        principal = p_i - interest if balance > 0 else 0
        if balance > 0:
            balance -= principal
        total_pmt = (p_i if balance > 0 else 0) + current_tax + ins
        
        # Still accumulate savings, but never use them for recasting
        savings += surplus
        
        cum_paid += total_pmt
        
        rows.append({
            "Month": m,
            "TotalPayment": total_pmt,
            "Tax": current_tax,
            "CumulativePaid": cum_paid,
            "Balance": balance,
            "IsPaidOff": balance <= 0,
            "SavingsBalance": savings
        })
            
    return pd.DataFrame(rows)

def calculate_tax_benefit(yearly_interest, property_tax, income, filing_status="married"):
    """Calculate tax benefit from mortgage interest and property tax deductions"""
    # Constants for 2025
    STANDARD_DEDUCTION = 29850 if filing_status == "married" else 14925
    SALT_LIMIT = 10000
    MORTGAGE_LIMIT = 750000
    
    # Limit mortgage interest deduction based on loan balance
    effective_ratio = min(MORTGAGE_LIMIT / loan, 1) if loan > 0 else 0
    deductible_interest = yearly_interest * effective_ratio
    
    # Calculate SALT (State And Local Tax) deduction
    deductible_salt = min(property_tax * 12, SALT_LIMIT)  # Property tax is monthly
    
    # Total itemized deductions
    total_itemized = deductible_interest + deductible_salt
    
    # Only beneficial if itemized > standard
    if total_itemized <= STANDARD_DEDUCTION:
        return 0
    
    # Calculate marginal benefit on amount over standard deduction
    excess_deduction = total_itemized - STANDARD_DEDUCTION
    
    # Get marginal rates
    if filing_status == "married":
        if income <= 203300:
            federal_marginal = 0.22
        elif income <= 398400:
            federal_marginal = 0.24
        elif income <= 504550:
            federal_marginal = 0.32
        elif income <= 755100:
            federal_marginal = 0.35
        else:
            federal_marginal = 0.37
    else:  # single
        if income <= 103350:
            federal_marginal = 0.22
        elif income <= 197300:
            federal_marginal = 0.24
        elif income <= 250525:
            federal_marginal = 0.32
        elif income <= 626350:
            federal_marginal = 0.35
        else:
            federal_marginal = 0.37
    
    # Get CA state marginal rate
    if filing_status == "married":
        if income <= 75576:
            state_marginal = 0.04
        elif income <= 104910:
            state_marginal = 0.06
        elif income <= 132590:
            state_marginal = 0.08
        elif income <= 677278:
            state_marginal = 0.093
        elif income <= 812728:
            state_marginal = 0.103
        elif income <= 1354550:
            state_marginal = 0.113
        else:
            state_marginal = 0.123
    else:  # single
        if income <= 37788:
            state_marginal = 0.04
        elif income <= 52455:
            state_marginal = 0.06
        elif income <= 66295:
            state_marginal = 0.08
        elif income <= 338639:
            state_marginal = 0.093
        elif income <= 406364:
            state_marginal = 0.103
        elif income <= 677275:
            state_marginal = 0.113
        else:
            state_marginal = 0.123
    
    # Combine rates and calculate tax benefit
    combined_marginal = federal_marginal + state_marginal
    tax_benefit = excess_deduction * combined_marginal
    
    return tax_benefit



# ---------------- Inputs ----------------
st.title("Mortgage Payment Simulator")
st.sidebar.header("Mortgage details")

price = st.sidebar.number_input("Purchase price ($)", 100_000, 10_000_000, 300000, step=25_000, format="%i")
down = st.sidebar.number_input("Down payment ($)", 0, price, int(price * 0.30), step=10_000, format="%i")
loan = price - down

col1, col2 = st.sidebar.columns(2)
with col1:
    rate = st.sidebar.number_input("Interest rate (%)", 0.1, 15.0, 6.6, step=0.05, format="%.2f")
with col2:
    term_years = st.sidebar.number_input("Term (years)", 5, 40, 30, step=1)

tax_method = st.sidebar.radio("Property tax input", ("Annual percentage", "Monthly amount"), horizontal=True)
if tax_method == "Monthly amount":
    tax_month = st.sidebar.number_input("Property tax ($/mo)", 0, 10_000, 1500, step=50, format="%i")
else:
    tax_pct = st.sidebar.number_input("Annual property tax (%)", 0.0, 5.0, 1.17, step=0.05, format="%.2f")
    tax_month = int(price * (tax_pct / 100) / 12)
    st.sidebar.caption(f"Monthly property tax: ${tax_month:,}")

tax_appreciation = st.sidebar.number_input("Annual property tax appreciation (%)", 0.0, 10.0, 2.0, step=0.1, format="%.1f")

ins_month = st.sidebar.number_input("Insurance ($/mo)", 0, 5_000, 300, step=25, format="%i")

st.sidebar.header("Recast strategy")
method = st.sidebar.radio("Method", ["Savings-based", "Fixed lump sum"], horizontal=True)
recast_int = st.sidebar.number_input("Months between recasts", 3, 60, 12, step=3)

initial_cash = st.sidebar.number_input("Initial cash ($)", 0, 2_000_000, 0, step=10_000, format="%i")

if method == "Savings-based":
    surplus = st.sidebar.number_input("Monthly savings ($)", 0, 50_000, 1_000, step=500, format="%i")
    buffer_cash = st.sidebar.number_input("Cash buffer ($)", 0, 1_000_000, 10_000, step=10_000, format="%i")
    lump = 0
else:
    lump = st.sidebar.number_input("Recast amount ($)", 0, 1_000_000, 90_000, step=10_000, format="%i")
    surplus = 0
    buffer_cash = 0

st.sidebar.header("Income scenarios (optional)")
use_secondary = st.sidebar.radio("Tax benefit calculation uses:", ["Primary Income", "Secondary Income"], horizontal=True)
col1, col2 = st.sidebar.columns(2)

with col1:
    st.markdown("**Primary Income**")
    gross_income = st.number_input("Primary gross annual income ($)", 0, 10_000_000, 200000, step=10_000, format="%i")
    manual_tax_rate1 = st.checkbox("Set tax rate manually (Primary)", False)
    if manual_tax_rate1:
        tax_rate = st.slider("Primary tax rate (%)", 0.0, 60.0, 40.0, step=0.5)
        st.write(f"**Effective rate: {tax_rate:.1f}%**")
    else:
        tax_rate = calculate_effective_tax_rate(gross_income)
        # Calculate marginal rates
        if gross_income <= 203300:
            federal_marginal = 22.0
        elif gross_income <= 398400:
            federal_marginal = 24.0
        elif gross_income <= 504550:
            federal_marginal = 32.0
        elif gross_income <= 755100:
            federal_marginal = 35.0
        else:
            federal_marginal = 37.0

        if gross_income <= 75576:
            state_marginal = 4.0
        elif gross_income <= 104910:
            state_marginal = 6.0
        elif gross_income <= 132590:
            state_marginal = 8.0
        elif gross_income <= 677278:
            state_marginal = 9.3
        elif gross_income <= 812728:
            state_marginal = 10.3
        elif gross_income <= 1354550:
            state_marginal = 11.3
        else:
            state_marginal = 12.3
            
        st.write("**Tax rates:**")
        st.write(f"Effective: **{tax_rate:.1f}%**")
        st.caption("Includes federal, CA state,")
        st.caption("SS (to $167,700) & Medicare")
        st.write(f"Marginal: **{federal_marginal + state_marginal:.1f}%**")
        st.caption(f"Federal: {federal_marginal:.1f}%")
        st.caption(f"CA State: {state_marginal:.1f}%")

with col2:
    st.markdown("**Secondary Income**")
    gross_income2 = st.number_input("Secondary gross annual income ($)", 0, 10_000_000, 100000, step=10_000, format="%i")
    manual_tax_rate2 = st.checkbox("Set tax rate manually (Secondary)", False)
    if manual_tax_rate2:
        tax_rate2 = st.slider("Secondary tax rate (%)", 0.0, 60.0, 40.0, step=0.5)
        st.write(f"**Effective rate: {tax_rate2:.1f}%**")
    else:
        tax_rate2 = calculate_effective_tax_rate(gross_income2)
        if gross_income2 > 0:
            # Calculate marginal rates
            if gross_income2 <= 203300:
                federal_marginal2 = 22.0
            elif gross_income2 <= 398400:
                federal_marginal2 = 24.0
            elif gross_income2 <= 504550:
                federal_marginal2 = 32.0
            elif gross_income2 <= 755100:
                federal_marginal2 = 35.0
            else:
                federal_marginal2 = 37.0

            if gross_income2 <= 75576:
                state_marginal2 = 4.0
            elif gross_income2 <= 104910:
                state_marginal2 = 6.0
            elif gross_income2 <= 132590:
                state_marginal2 = 8.0
            elif gross_income2 <= 677278:
                state_marginal2 = 9.3
            elif gross_income2 <= 812728:
                state_marginal2 = 10.3
            elif gross_income2 <= 1354550:
                state_marginal2 = 11.3
            else:
                state_marginal2 = 12.3
            
        st.write("**Tax rates:**")
        st.write(f"Effective: **{tax_rate2:.1f}%**")
        st.caption("Includes federal, CA state,")
        st.caption("SS (to $167,700) & Medicare")
        st.write(f"Marginal: **{federal_marginal2 + state_marginal2:.1f}%**")
        st.caption(f"Federal: {federal_marginal2:.1f}%")
        st.caption(f"CA State: {state_marginal2:.1f}%")

baseline_spend = st.sidebar.number_input("Baseline non-housing spend ($/mo)", 0, 50_000, 0, step=500, format="%i")

# Calculate term_mo before we need it
term_mo = term_years * 12

st.sidebar.header("Chart settings")
max_months = st.sidebar.number_input("Time horizon (months)", 12, term_mo, 96, step=12)

include_tax_refund = st.sidebar.checkbox("Include future tax refund in effective payment", True,
                                       help="When checked, subtracts estimated tax benefits from the payment amount. Uncheck to see raw payment before tax benefits.")

# ---------------- Simulation ----------------
monthly_rate = rate / 100 / 12
df = simulate(term_mo, monthly_rate, tax_month, ins_month)
df_no_recast = simulate_no_recast(term_mo, monthly_rate, tax_month, ins_month)

# Trim dataframes to max_months
df = df[df['Month'] <= max_months].copy()
df_no_recast = df_no_recast[df_no_recast['Month'] <= max_months].copy()

# ---------------- Charts ----------------
st.subheader("Monthly payment")
recast_points = df[df['RecastAmount'] > 0].copy()

# Define a modern dark color palette
colors = {
    'primary': '#E5E9F0',      # Light grey text
    'secondary': '#88C0D0',    # Light blue
    'accent1': '#A3BE8C',      # Sage green
    'accent2': '#B48EAD',      # Lavender
    'highlight': '#EBCB8B',    # Warm yellow
    'grid': '#4C566A',         # Dark blue-grey for grid
    'background': '#2E3440'    # Dark background
}

# Define base layout template for all plots
plot_template = dict(
    layout=dict(
        paper_bgcolor=colors['background'],
        plot_bgcolor=colors['background'],
        font=dict(
            family="Arial, sans-serif",
            color=colors['primary']
        ),
        xaxis=dict(
            gridcolor=colors['grid'],
            showline=True,
            linewidth=1,
            linecolor=colors['grid'],
            showgrid=True,
            tickfont=dict(color=colors['primary']),
            title_font=dict(color=colors['primary'])
        ),
        yaxis=dict(
            gridcolor=colors['grid'],
            showline=True,
            linewidth=1,
            linecolor=colors['grid'],
            showgrid=True,
            tickfont=dict(color=colors['primary']),
            title_font=dict(color=colors['primary'])
        )
    )
)
# Also add initial payment point
initial_point = pd.DataFrame({
    'Month': [0],
    'TotalPayment': [df['TotalPayment'].iloc[0]],
    'EffectivePayment': [df['EffectivePayment'].iloc[0]],
    'RecastAmount': [0],
    'P&I': [df['P&I'].iloc[0]]
})

if len(recast_points) > 0:
    # For each recast point, create a copy of the next row to show payment after recast
    next_points = recast_points.copy()
    next_points['Month'] = next_points['Month'] + 1
    
    # Get payment values from after each recast
    for idx in next_points.index:
        month = next_points.loc[idx, 'Month']
        if month < len(df):
            next_points.loc[idx, 'TotalPayment'] = df.loc[df['Month'] == month, 'TotalPayment'].values[0]
            next_points.loc[idx, 'EffectivePayment'] = df.loc[df['Month'] == month, 'EffectivePayment'].values[0]
else:
    next_points = initial_point

next_points = pd.concat([initial_point, next_points], ignore_index=True)

# Create monthly payments figure
fig1 = go.Figure()

# Monthly payment lines - Effective Payment first so it's the primary line
# Use either effective payment (with tax benefit) or total payment as the primary line based on toggle
if include_tax_refund:
    fig1.add_trace(
        go.Scatter(x=df['Month'], y=df['EffectivePayment'],
                  name='Effective Payment', line=dict(color='red', width=3)))
    fig1.add_trace(
        go.Scatter(x=df['Month'], y=df['TotalPayment'],
                  name='Total Payment', line=dict(color='gray', dash='dot')))
else:
    fig1.add_trace(
        go.Scatter(x=df['Month'], y=df['TotalPayment'],
                  name='Total Payment', line=dict(color='red', width=3)))
    fig1.add_trace(
        go.Scatter(x=df['Month'], y=df['EffectivePayment'],
                  name='Effective Payment', line=dict(color='gray', dash='dot')))

fig1.add_trace(
    go.Scatter(x=df['Month'], y=df['P&I'],
              name='P&I', line=dict(color='blue')))

fig1.add_trace(
    go.Scatter(x=df['Month'], y=df['Tax'],
              name='Tax', line=dict(color='green')))

fig1.add_trace(
    go.Scatter(x=df['Month'], y=df['MonthlyTaxBenefit'],
              name='Tax Benefit', line=dict(color='purple', dash='dot')))

# Add recast indicators
fig1.add_trace(
    go.Scatter(
        x=next_points['Month'],
        y=next_points['EffectivePayment'] if include_tax_refund else next_points['TotalPayment'],
        mode='markers+text',
        marker=dict(symbol='star', size=12, color='red'),
        text=[f'${y:,.0f}' for y in (next_points['EffectivePayment'] if include_tax_refund else next_points['TotalPayment'])],
        textposition='top center',
        name='Payment after Recast',
        customdata=next_points['TotalPayment'],
        hovertemplate='Month: %{x}<br>' + 
                     ('Effective' if include_tax_refund else 'Total') + 
                     ' Payment: $%{y:,.2f}<br>Total Payment: $%{customdata:,.2f}'
    ))

# Update monthly payments figure layout
fig1.update_layout(
    height=500,
    title=dict(text='Monthly Payments & Tax Benefits', x=0.5),
    showlegend=True,
    legend=dict(
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0.01,
        orientation="h",
        title=dict(text="Monthly Payments", font=dict(size=12))
    ),
    yaxis_title="Monthly Payment ($)",
    xaxis_title="Month"
)

st.plotly_chart(fig1)

st.subheader("Cumulative costs")
# Create cumulative costs figure
fig2 = go.Figure()

fig2.add_trace(
    go.Scatter(x=df['Month'], y=df['CumulativePaid'],
              name='Cumulative Cost (with recast)',
              line=dict(color='red', width=3)))

fig2.add_trace(
    go.Scatter(x=df_no_recast['Month'], y=df_no_recast['CumulativePaid'],
              name='Cumulative Cost (no recast)',
              line=dict(color='gray', dash='dot')))

fig2.add_trace(
    go.Scatter(x=df['Month'], y=df['Balance'],
              name='Loan Balance',
              line=dict(color='blue')))

# Update cumulative costs figure layout
fig2.update_layout(
    height=500,
    title=dict(text='Cumulative Cost & Balance', x=0.5),
    showlegend=True,
    legend=dict(
        yanchor="bottom",
        y=1.02,
        xanchor="left",
        x=0.01,
        orientation="h",
        title=dict(text="Cumulative Analysis", font=dict(size=12))
    ),
    yaxis_title="Amount ($)",
    xaxis_title="Month"
)

st.plotly_chart(fig2)

# ---------------- Income Ratio Plot ----------------
if gross_income > 0 or gross_income2 > 0:
    st.subheader("Income Ratios")
    
    fig3 = go.Figure()
    
    # Calculate monthly values
    monthly_gross1 = gross_income / 12
    monthly_gross2 = gross_income2 / 12
    monthly_net1 = (gross_income * (1 - tax_rate/100)) / 12
    monthly_net2 = (gross_income2 * (1 - tax_rate2/100)) / 12
    
    # Calculate ratios for each income stream - use either effective or total payment based on toggle
    payment_column = 'EffectivePayment' if include_tax_refund else 'TotalPayment'
    primary_ratio_gross = ((df[payment_column] + baseline_spend) / monthly_gross1 * 100) if monthly_gross1 > 0 else df[payment_column] * 0
    primary_ratio_net = ((df[payment_column] + baseline_spend) / monthly_net1 * 100) if monthly_net1 > 0 else df[payment_column] * 0
    secondary_ratio_gross = ((df[payment_column] + baseline_spend) / monthly_gross2 * 100) if monthly_gross2 > 0 else df[payment_column] * 0
    secondary_ratio_net = ((df[payment_column] + baseline_spend) / monthly_net2 * 100) if monthly_net2 > 0 else df[payment_column] * 0
    
    # Add traces
    if gross_income > 0:
        fig3.add_trace(
            go.Scatter(x=df['Month'], y=primary_ratio_gross,
                      name='Gross Income',
                      legendgroup='Primary',
                      legendgrouptitle_text='Primary Income',
                      line=dict(color='red', width=3)))
        fig3.add_trace(
            go.Scatter(x=df['Month'], y=primary_ratio_net,
                      name='Net Income',
                      legendgroup='Primary',
                      line=dict(color='darkred', width=3)))
    
    if gross_income2 > 0:
        fig3.add_trace(
            go.Scatter(x=df['Month'], y=secondary_ratio_gross,
                      name='Gross Income',
                      legendgroup='Secondary',
                      legendgrouptitle_text='Secondary Income',
                      line=dict(color='blue', width=3)))
        fig3.add_trace(
            go.Scatter(x=df['Month'], y=secondary_ratio_net,
                      name='Net Income',
                      legendgroup='Secondary',
                      line=dict(color='darkblue', width=3)))
    
    # Update layout
    fig3.update_layout(
        height=500,
        title=dict(text='Payment-to-Income Ratios Over Time', x=0.5),
        showlegend=True,
        legend=dict(
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.01,
            orientation="h",
            title=dict(text="Income Scenarios", font=dict(size=12))
        ),
        yaxis_title="Percent of Income (%)",
        xaxis_title="Month"
    )
    
    st.plotly_chart(fig3)
    
    # Add some explanatory text
    st.caption("""
    - All ratios include both effective housing payment and baseline non-housing spend
    - Gross ratios use pre-tax income, Net ratios use post-tax income
    - Primary/Secondary scenarios show payment burden under different income assumptions
    """)

    # ---------------- Housing-only Ratio Plot ----------------
    st.subheader("Housing-only Income Ratios")

    fig4 = go.Figure()
    
    # Calculate housing-only ratios (without baseline spend)
    # Use either total or effective payment based on toggle
    payment_column = 'EffectivePayment' if include_tax_refund else 'TotalPayment'
    primary_ratio_gross_housing = (df[payment_column] / monthly_gross1 * 100) if monthly_gross1 > 0 else df[payment_column] * 0
    primary_ratio_net_housing = (df[payment_column] / monthly_net1 * 100) if monthly_net1 > 0 else df[payment_column] * 0
    secondary_ratio_gross_housing = (df[payment_column] / monthly_gross2 * 100) if monthly_gross2 > 0 else df[payment_column] * 0
    secondary_ratio_net_housing = (df[payment_column] / monthly_net2 * 100) if monthly_net2 > 0 else df[payment_column] * 0
    
    # Add threshold lines with clearer colors and better visibility
    fig4.add_hline(y=28, 
                   line=dict(color='rgba(255,165,0,0.5)', width=2, dash='dot'),
                   annotation=dict(text='28% Threshold', align='left', xanchor='left',
                                 yanchor='bottom', x=1.02, y=28))
    fig4.add_hline(y=36, 
                   line=dict(color='rgba(255,0,0,0.5)', width=2, dash='dot'),
                   annotation=dict(text='36% Threshold', align='left', xanchor='left',
                                 yanchor='bottom', x=1.02, y=36))
    
    # Add traces
    if gross_income > 0:
        fig4.add_trace(
            go.Scatter(x=df['Month'], y=primary_ratio_gross_housing,
                      name='Gross Income',
                      legendgroup='Primary',
                      legendgrouptitle_text='Primary Income',
                      line=dict(color='red', width=3)))
        fig4.add_trace(
            go.Scatter(x=df['Month'], y=primary_ratio_net_housing,
                      name='Net Income',
                      legendgroup='Primary',
                      line=dict(color='darkred', width=3)))
    
    if gross_income2 > 0:
        fig4.add_trace(
            go.Scatter(x=df['Month'], y=secondary_ratio_gross_housing,
                      name='Gross Income',
                      legendgroup='Secondary',
                      legendgrouptitle_text='Secondary Income',
                      line=dict(color='blue', width=3)))
        fig4.add_trace(
            go.Scatter(x=df['Month'], y=secondary_ratio_net_housing,
                      name='Net Income',
                      legendgroup='Secondary',
                      line=dict(color='darkblue', width=3)))
    
    # Update layout
    fig4.update_layout(
        height=500,
        title=dict(text='Housing-only DTI Ratios Over Time', x=0.5),
        showlegend=True,
        legend=dict(
            yanchor="bottom",
            y=1.02,
            xanchor="left",
            x=0.01,
            orientation="h",
            title=dict(text="Income Scenarios", font=dict(size=12))
        ),
        yaxis_title="Debt-to-Income Ratio (%)",
        xaxis_title="Month"
    )
    
    st.plotly_chart(fig4)
    
    # Add explanatory text for housing-only ratios
    st.caption(f"""
    - Housing-only DTI ratios show {'effective' if include_tax_refund else 'raw'} housing costs ({f'after' if include_tax_refund else 'before'} tax benefits) as a percentage of income
    - 28% threshold: Traditional front-end DTI limit for housing costs (PITI)
    - 36% threshold: Traditional back-end DTI limit including all debt payments
    - Gross ratios use pre-tax income, Net ratios use post-tax income
    """)

# ---------------- Stats ----------------
# Calculate total costs over the displayed period
total_paid = df['TotalPayment'].sum()
total_tax_benefit = df['MonthlyTaxBenefit'].sum()
total_effective_cost = total_paid - total_tax_benefit
ending_balance = df['Balance'].iloc[-1]
total_cost = total_paid + ending_balance

# Display statistics
st.subheader("Summary Statistics")
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Payments", f"${total_paid:,.0f}")
with col2:
    st.metric("Total Tax Benefit", f"${total_tax_benefit:,.0f}")
with col3:
    st.metric("Total Effective Cost", f"${total_effective_cost:,.0f}")

# Income analysis
if gross_income > 0 or gross_income2 > 0:
    st.subheader("Income Analysis")
    
    # Calculate monthly take-home pay
    if gross_income > 0:
        monthly_income1 = (gross_income * (1 - tax_rate/100)) / 12
    else:
        monthly_income1 = 0
        
    if gross_income2 > 0:
        monthly_income2 = (gross_income2 * (1 - tax_rate2/100)) / 12
    else:
        monthly_income2 = 0
    
    total_monthly_income = monthly_income1 + monthly_income2
    
    # Get average monthly housing cost
    avg_effective_pmt = df['EffectivePayment'].mean()
    
    # Calculate disposable income
    disposable = total_monthly_income - avg_effective_pmt - baseline_spend
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Monthly Take-Home Pay", f"${total_monthly_income:,.0f}")
    with col2:
        st.metric("Avg Monthly Housing Cost", f"${avg_effective_pmt:,.0f}")
    with col3:
        st.metric("Monthly Disposable", f"${disposable:,.0f}")
        
    # Calculate and display DTI
    gross_monthly = (gross_income + gross_income2) / 12
    if gross_monthly > 0:
        front_end_dti = (df['P&I'].iloc[0] + tax_month + ins_month) / gross_monthly * 100
        st.metric("Front-end DTI", f"{front_end_dti:.1f}%")