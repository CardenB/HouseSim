import streamlit as st
import pandas as pd
import numpy as np
import altair as alt

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
            "SavingsBalance": savings
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

# ---------------- Inputs ----------------
st.title("Mortgage Payment Simulator")
st.sidebar.header("Mortgage details")

price = st.sidebar.number_input("Purchase price ($)", 100_000, 10_000_000, 1_800_000, step=25_000, format="%i")
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

initial_cash = st.sidebar.number_input("Initial cash ($)", 0, 2_000_000, 200_000, step=10_000, format="%i")

if method == "Savings-based":
    surplus = st.sidebar.number_input("Monthly savings ($)", 0, 50_000, 8_000, step=500, format="%i")
    buffer_cash = st.sidebar.number_input("Cash buffer ($)", 0, 1_000_000, 150_000, step=10_000, format="%i")
    lump = 0
else:
    lump = st.sidebar.number_input("Recast amount ($)", 0, 1_000_000, 90_000, step=10_000, format="%i")
    surplus = 0
    buffer_cash = 0

st.sidebar.header("Income scenarios (optional)")
col1, col2 = st.sidebar.columns(2)

with col1:
    st.markdown("**Primary Income**")
    gross_income = st.number_input("Primary gross annual income ($)", 0, 10_000_000, 690_000, step=10_000, format="%i")
    manual_tax_rate1 = st.checkbox("Set tax rate manually (Primary)", False)
    if manual_tax_rate1:
        tax_rate = st.slider("Primary tax rate (%)", 0.0, 60.0, 40.0, step=0.5)
    else:
        tax_rate = calculate_effective_tax_rate(gross_income)
        st.write(f"Calculated effective tax rate: **{tax_rate:.1f}%**")
        st.caption("Includes federal, CA state, Social Security (up to $167,700), and Medicare tax (married filing jointly)")

with col2:
    st.markdown("**Secondary Income**")
    gross_income2 = st.number_input("Secondary gross annual income ($)", 0, 10_000_000, 260000, step=10_000, format="%i")
    manual_tax_rate2 = st.checkbox("Set tax rate manually (Secondary)", False)
    if manual_tax_rate2:
        tax_rate2 = st.slider("Secondary tax rate (%)", 0.0, 60.0, 40.0, step=0.5)
    else:
        tax_rate2 = calculate_effective_tax_rate(gross_income2)
        st.write(f"Calculated effective tax rate: **{tax_rate2:.1f}%**")
        st.caption("Includes federal, CA state, Social Security (up to $167,700), and Medicare tax (married filing jointly)")

baseline_spend = st.sidebar.number_input("Baseline non-housing spend ($/mo)", 0, 50_000, 0, step=500, format="%i")

# Calculate term_mo before we need it
term_mo = term_years * 12

st.sidebar.header("Chart settings")
max_months = st.sidebar.number_input("Time horizon (months)", 12, term_mo, 96, step=12)

# ---------------- Simulation ----------------
monthly_rate = rate / 100 / 12
df = simulate(term_mo, monthly_rate, tax_month, ins_month)
df_no_recast = simulate_no_recast(term_mo, monthly_rate, tax_month, ins_month)

# Trim dataframes to max_months
df = df[df['Month'] <= max_months].copy()
df_no_recast = df_no_recast[df_no_recast['Month'] <= max_months].copy()

# ---------------- Charts ----------------
st.subheader("Monthly payment (excluding recast)")
recast_points = df[df['RecastAmount'] > 0].copy()

# Base monthly payment line
base = alt.Chart(df).mark_line().encode(
    x=alt.X("Month", scale=alt.Scale(domain=[0, max_months])),
    y=alt.Y("TotalPayment", title="Monthly Payment ($)")
)

# Add recast point markers and labels
if not recast_points.empty:
    # Add markers for recast points
    markers = alt.Chart(recast_points).mark_point(
        size=100,
        shape='triangle',
        filled=True,
        color='red'
    ).encode(
        x="Month",
        y="TotalPayment",
        tooltip=[
            alt.Tooltip("Month", title="Month"),
            alt.Tooltip("RecastAmount", format="$,.0f", title="Recast Amount"),
            alt.Tooltip("P&I", format="$,.0f", title="New P&I Payment"),
            alt.Tooltip("TotalPayment", format="$,.0f", title="New Total Payment")
        ]
    )
    
    # Add labels for new P&I amount after recast
    labels = alt.Chart(recast_points).mark_text(
        align='left',
        baseline='bottom',
        dx=5,
        dy=-10,
        fontSize=10,
        color='red'
    ).encode(
        x="Month",
        y="TotalPayment",
        text=alt.Text("TotalPayment:Q", format="$,.0f")  # Changed from "P&I:Q" to "TotalPayment:Q"
    )
    
    chart = (base + markers + labels).interactive()
else:
    chart = base.interactive()

st.altair_chart(chart, use_container_width=True)
if len(recast_points) > 0:
    st.caption("Note: Red triangles show recast points. Labels show new total monthly payment (PITI) after each recast.")

st.subheader("Cumulative payments comparison")

# Create trimmed versions of the data for plotting
df_plot = df.copy()
df_no_recast_plot = df_no_recast.copy()

df_plot["Strategy"] = "With recast"
df_no_recast_plot["Strategy"] = "Without recast"

# Ensure all required columns exist before combining
df_plot["CumulativeSavings"] = 0.0  # Initialize with zeros
df_no_recast_plot["CumulativeSavings"] = 0.0

# Calculate savings only if we have data to compare
min_months = min(len(df_plot), len(df_no_recast_plot))
if min_months > 0:
    df_plot["CumulativeSavings"] = df_no_recast_plot["CumulativePaid"].values - df_plot["CumulativePaid"].values

# Handle case where recast scenario pays off loan early
if len(df_plot) < len(df_no_recast_plot):
    remaining_tax_ins = (tax_month + ins_month) * (len(df_no_recast_plot) - len(df_plot))
    df_plot["CumulativeSavings"] = df_plot["CumulativeSavings"] + remaining_tax_ins

# Combine the dataframes for plotting and ensure clean data
df_combined = pd.concat([df_plot, df_no_recast_plot]).reset_index(drop=True)
df_combined = df_combined.fillna(0)  # Replace any NaN values with 0

# Create yearly interval points for labels
df_labels = df_combined[
    (df_combined['Month'] % 12 == 0) & 
    (df_combined['Month'] <= max_months)
].copy()

# Create recast points for the recast strategy, ensuring they're within time horizon
recast_points = df_plot[
    (df_plot['RecastAmount'] > 0) & 
    (df_plot['Month'] <= max_months)
].copy()

# Base line chart for cumulative payments
try:
    cumulative_base = alt.Chart(df_combined).mark_line().encode(
        x=alt.X("Month", scale=alt.Scale(domain=[0, max_months])),
        y=alt.Y("CumulativePaid", title="Cumulative Payments ($)"),
        color=alt.Color("Strategy", legend=alt.Legend(title=None))
    )

    # Add text labels for yearly points only if we have labels to show
    if not df_labels.empty:
        labels = alt.Chart(df_labels).mark_text(
            align='left',
            baseline='middle',
            dx=5,
            fontSize=10
        ).encode(
            x="Month",
            y="CumulativePaid",
            text=alt.Text("CumulativePaid:Q", format="$,.0f"),
            color=alt.Color("Strategy", legend=None)
        )
        cumulative_base = cumulative_base + labels

    # Add recast points only if we have any within the time horizon
    if not recast_points.empty:
        recast_markers = alt.Chart(recast_points).mark_point(
            size=100,
            shape='triangle',
            filled=True,
            color='red'
        ).encode(
            x="Month",
            y="CumulativePaid",
            tooltip=["Month", 
                    alt.Tooltip("RecastAmount", format="$,.0f", title="Recast Amount"),
                    alt.Tooltip("CumulativeRecast", format="$,.0f", title="Total Recast"),
                    alt.Tooltip("CumulativeSavings", format="$,.0f", title="Savings at this point")]
        )
        cumulative_base = cumulative_base + recast_markers

    st.altair_chart(cumulative_base.interactive(), use_container_width=True)

except Exception as e:
    st.error("Unable to display cumulative payments chart. Please try adjusting the time horizon.")
    print(f"Chart error: {str(e)}")  # For debugging

# Add a summary of recast amounts and savings
col1, col2 = st.columns(2)
with col1:
    if df['RecastAmount'].sum() > 0:
        total_recast = df['RecastAmount'].sum()
        st.metric("Total recast amount", f"${total_recast:,.0f}")

with col2:
    # Calculate savings at the selected time horizon using the trimmed dataframes
    current_savings = df_no_recast.iloc[-1]["CumulativePaid"] - df.iloc[-1]["CumulativePaid"]
    st.metric("Total savings", f"${current_savings:,.0f}")
    
    # Show when loan is paid off if applicable, respecting the time horizon
    if df['IsPaidOff'].any():
        payoff_month = df[df['IsPaidOff']].iloc[0]['Month']
        if payoff_month <= max_months:
            st.caption(f"Loan paid off in month **{payoff_month}**")
    if df_no_recast['IsPaidOff'].any():
        payoff_month = df_no_recast[df_no_recast['IsPaidOff']].iloc[0]['Month']
        if payoff_month <= max_months:
            st.caption(f"Without recast, loan paid off in month **{payoff_month}**")

# ---------------- Income overlay ----------------
if gross_income > 0 or gross_income2 > 0:
    st.subheader("Payment vs. income ratios")
    income_df = pd.DataFrame()
    
    if gross_income > 0:
        gross_income_mo = gross_income / 12
        net_income_mo = (gross_income * (1 - tax_rate / 100)) / 12
        income_df["Primary - Post-tax"] = df["TotalPayment"] / net_income_mo
        income_df["Primary - Pre-tax"] = df["TotalPayment"] / gross_income_mo
        st.write(f"Primary monthly income: **${gross_income_mo:,.0f}** (pre-tax) / **${net_income_mo:,.0f}** (post-tax)")
        
    if gross_income2 > 0:
        gross_income_mo2 = gross_income2 / 12
        net_income_mo2 = (gross_income2 * (1 - tax_rate2 / 100)) / 12
        income_df["Secondary - Post-tax"] = df["TotalPayment"] / net_income_mo2
        income_df["Secondary - Pre-tax"] = df["TotalPayment"] / gross_income_mo2
        st.write(f"Secondary monthly income: **${gross_income_mo2:,.0f}** (pre-tax) / **${net_income_mo2:,.0f}** (post-tax)")
    
    if not income_df.empty:
        income_df.index = df["Month"]
        
        # Create income comparison chart
        income_data = pd.melt(income_df.reset_index(), id_vars=['Month'], var_name='Income Type', value_name='PITI Ratio')
        
        # Use different colors for pre and post-tax lines
        income_chart = alt.Chart(income_data).mark_line().encode(
            x="Month",
            y=alt.Y("PITI Ratio", title="PITI to Income Ratio"),
            color=alt.Color(
                "Income Type", 
                legend=alt.Legend(title=None),
                sort=['Primary - Pre-tax', 'Primary - Post-tax', 'Secondary - Pre-tax', 'Secondary - Post-tax']
            ),
            strokeDash=alt.condition(
                "indexof(datum['Income Type'], 'Pre-tax') >= 0",  # Use indexof instead of contains
                alt.value([5,5]),  # dashed line for pre-tax
                alt.value([0])     # solid line for post-tax
            )
        ).interactive()
        
        st.altair_chart(income_chart, use_container_width=True)
        st.caption("Solid lines show post-tax ratios, dashed lines show pre-tax ratios")

# ---------------- Table ----------------
with st.expander("Detailed numbers"):
    st.dataframe(df.style.format({
        "P&I": "${:,.0f}",
        "Tax": "${:,.0f}",
        "TotalPayment": "${:,.0f}",
        "CumulativePaid": "${:,.0f}",
        "Balance": "${:,.0f}"
    }))

st.caption("Model assumes constant property-tax and insurance. Lump sums are applied "
           "either from extra savings (after maintaining a cash buffer) or as fixed "
           "amounts every chosen interval. Recasting re-amortizes the loan with the "
           "same maturity date (no new term reset).")

# Add savings balance chart after the cumulative payments chart
if method == "Savings-based" or initial_cash > 0:
    st.subheader("Savings balance comparison")
    
    # Create combined savings data
    df_plot["Strategy"] = "With recast"
    df_no_recast_plot["Strategy"] = "Without recast"
    
    savings_combined = pd.concat([
        df_plot[["Month", "SavingsBalance", "Strategy"]],
        df_no_recast_plot[["Month", "SavingsBalance", "Strategy"]]
    ])
    
    # Base savings lines
    savings_chart = alt.Chart(savings_combined).mark_line().encode(
        x=alt.X("Month", scale=alt.Scale(domain=[0, max_months])),
        y=alt.Y("SavingsBalance", title="Savings Balance ($)"),
        color=alt.Color("Strategy", legend=alt.Legend(title=None))
    )
    
    # Add recast markers to savings chart
    if not recast_points.empty:
        savings_recast_markers = alt.Chart(recast_points).mark_point(
            size=100,
            shape='triangle',
            filled=True,
            color='red'
        ).encode(
            x="Month",
            y="SavingsBalance",
            tooltip=["Month", 
                    alt.Tooltip("RecastAmount", format="$,.0f", title="Recast Amount"),
                    alt.Tooltip("SavingsBalance", format="$,.0f", title="Savings After Recast")]
        )
        savings_chart = (savings_chart + savings_recast_markers)
    
    st.altair_chart(savings_chart.interactive(), use_container_width=True)
    
    # Show final savings comparison
    col1, col2 = st.columns(2)
    with col1:
        final_savings_recast = df_plot.iloc[-1]["SavingsBalance"]
        st.metric("Final savings with recast", f"${final_savings_recast:,.0f}")
    with col2:
        final_savings_no_recast = df_no_recast_plot.iloc[-1]["SavingsBalance"]
        st.metric("Final savings without recast", f"${final_savings_no_recast:,.0f}")
        
    savings_difference = final_savings_no_recast - final_savings_recast
    if savings_difference > 0:
        st.caption(f"Without recasting, you would have **${savings_difference:,.0f}** more in savings, "
                  f"but your loan balance would be higher. See cumulative payments chart above for total cost comparison.")