import csv
import requests
import os

############################################
# Functions taken from flask app helpers.py
############################################
def calculate_monthly_debt(certn_data):
    def _as_monthly_payment(trade):
        if not trade:
            return 0
        if [True for i in trade.get('narratives') if 'Monthly' in i]:
            return float(trade['payment_term_amount'])
        elif [True for i in trade.get('narratives') if 'Semi-monthly' in i]:
            return float(trade['payment_term_amount']) * 2
        elif [True for i in trade.get('narratives') if 'Bi-weekly' in i]:
            return (float(trade['payment_term_amount']) * 26) / 12
        else:
            return float(trade.get('payment_term_amount')) if trade.get('payment_term_amount') else 0
    def _is_valid_narrative(narratives):
        narratives_to_exclude = ['Written-off', 'Account paid', 'bankruptcy']
        return not any([[True for k in narratives if i in k] for i in narratives_to_exclude])
    total = 0
    payments = certn_data['equifax_result'].get('trades')
    for i in payments:
        if i.get('payment_term_amount') and i.get('percent_credit_used', 0) not in [0, '0.00', None] and _is_valid_narrative(i.get('narratives')):
            total += _as_monthly_payment(i)
    return int(total)

def string_to_int(string):
    try:
        return int(float(string))
    except:
        return 0
############################################

#get_rent_to_income(rent, income) returns the SK score impact of the rent to income ratio as a decimal
def get_rent_to_income_impact(rent, income):
    if rent == 0 or income == 0:
        return 0
    ratio = rent / income * 100
    if ratio < 20:
        return 0.10
    elif ratio < 30:
        return 0.05
    elif ratio < 60:
        return 0
    elif ratio < 80:
        return -0.05
    else:
        return -0.10

# #get_annual_income(ai, pi, oi) returns the total annual income by combining annual income, partner income, and other income
# def get_annual_income(ai, pi, oi):
#     total_income = 0
#     if ai != 'NULL':
#         total_income += string_to_int(ai)
#     if pi != 'NULL':
#         total_income += string_to_int(pi)
#     if oi != 'NULL':
#         total_income += string_to_int(oi)
#     return total_income

#get_monthy_debt(debt) returns the SK score impact of the monthly debt as a decimal
def get_monthly_debt_impact(debt):
    if debt < 500:
        return 0.05
    elif debt < 1000:
        return 0
    elif debt < 1500:
        return -0.05
    else:
        return -0.10

#get_sk_score(certn_score, positive_diff
#depending on the certn_score, the positive_impact and negative_impact will be scaled down by a factor of positive_impact_factor and negative_impact_factor
def get_sk_score(certn_score, positive_impact, negative_impact):
    positive_impact_factor = 1
    negative_impact_factor = 1
    counter = 40
    impact_factors = { # {upper bound: (positive impact factor, negative impact factor)}
        40: (1, 0),
        50: (0.9, 0.3),
        60: (0.8, 0.4),
        70: (0.7, 0.5),
        80: (0.6, 0.6),
        90: (0.5, 0.7),
        100: (0.4, 0.8),
        110: (0, 0.9)
    }
    while counter <= 110:
        if certn_score >= 99:
            positive_impact_factor, negative_impact_factor = impact_factors[110]
            break
        elif certn_score < counter:
            positive_impact_factor, negative_impact_factor = impact_factors[counter]
            break
        else:
            counter += 10
    sk_score = certn_score * (1 + positive_impact_factor * positive_impact + negative_impact_factor * negative_impact)
    if sk_score < 1: sk_score = 1
    if sk_score > 99: sk_score = 99
    return int(float(sk_score))

with open('test.csv', 'r') as f:
    reader = csv.reader(f)
    next(reader)
    counter = 1
    with open('sk.csv', 'w', newline='') as file:
        writer = csv.writer(file)
        writer.writerow(["Certn Score", "Rent/Income", "Monthly Debt", "SK Score"])
        for row in reader:
            if counter > 70:
                break
            print(counter,": ", row)
            counter += 1
            certn_data = requests.get(f"https://api.certn.co/api/v2/applicants/{row[1]}", headers={"Authorization": f"Bearer {os.environ['CERTN_API_KEY']}"}).json()
            certn_score = int(float(certn_data['certn_score']))
            monthly_rent = string_to_int(row[2])
            monthly_income = (
                string_to_int(row[3]) + string_to_int(row[4]) + string_to_int(row[5])
            ) / 12
            positive_impact = 0
            negative_impact = 0

            impacts = [
                get_rent_to_income_impact(monthly_rent, monthly_income),
                get_monthly_debt_impact(calculate_monthly_debt(certn_data)),
            ]

            for impact in impacts:
                if impact > 0:
                    positive_impact += impact
                else:
                    negative_impact += impact

            sk_score = get_sk_score(certn_score, positive_impact, negative_impact)
            writer.writerow([f"{certn_score}", f"{monthly_rent / monthly_income if monthly_income else 'Invalid Income'}", f"{calculate_monthly_debt(certn_data)}", f"{sk_score}"])
