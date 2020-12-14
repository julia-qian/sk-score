import csv
import requests
import os

# should update this to match with most recent on master
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

def get_rent_to_income(rent, income):
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

def string_to_int(string):
    try:
        return int(float(string))
    except:
        return 0

def get_annual_income(ai, pi, oi):
    retval = 0
    if ai != 'NULL':
        retval += string_to_int(ai)
    if pi != 'NULL':
        retval += string_to_int(pi)
    if oi != 'NULL':
        retval += string_to_int(oi)
    return retval

def get_monthly_debt(debt):
    if debt < 500:
        return 0.05
    elif debt < 1000:
        return 0
    elif debt < 1500:
        return -0.05
    else:
        return -0.10

def get_sk_score(certn_score, positive_diff, negative_diff):
    pf = 1
    nf = 1
    counter = 40
    # {upper bound: (positive impact, negative impact)}
    impact_ranges = {
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
            pf, nf = impact_ranges[110]
            break
        elif certn_score < counter:
            pf, nf = impact_ranges[counter]
            break
        else:
            counter += 10
    retval = certn_score * (1 + pf * positive_diff + nf * negative_diff)
    return int(retval)


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
            monthly_rent = int(row[2].replace(",","")) if row[2] != 'NULL' else 0
            monthly_income = get_annual_income(row[3], row[4], row[5]) / 12
            positive_diff = 0
            negative_diff = 0

            factors = [
                get_rent_to_income(monthly_rent, monthly_income),
                get_monthly_debt(calculate_monthly_debt(certn_data)),
            ]

            for factor in factors:
                if factor > 0:
                    positive_diff += factor
                else:
                    negative_diff += factor

            sk_score = get_sk_score(certn_score, positive_diff, negative_diff)
            if sk_score < 1: sk_score = 1
            if sk_score > 99: sk_score = 99
            writer.writerow([f"{certn_score}", f"{monthly_rent / monthly_income if monthly_income else 'Invalid Income'}", f"{calculate_monthly_debt(certn_data)}", f"{sk_score}"])

# with open('test.csv', 'r') as f:
#     reader = csv.reader(f)
#     next(reader)
#     counter = 0
#     for row in reader:
#         if counter > 9:
#             break
#         counter += 1

#         certn_data = requests.get(f"https://api.certn.co/api/v2/applicants/bca338e0-1ffe-4409-a217-3d024603ed95", headers={"Authorization": f"Bearer {os.environ['CERTN_API_KEY']}"}).json()
#         certn_score = int(float(certn_data['certn_score']))
#         monthly_rent = int(row[2].replace(",","")) if row[2] != 'NULL' else 0
#         monthly_income = get_annual_income(row[3], row[4], row[5]) / 12
#         positive_diff = 0
#         negative_diff = 0

#         factors = [
#             get_rent_to_income(monthly_rent, monthly_income),
#             get_monthly_debt(calculate_monthly_debt(certn_data)),
#         ]

#         for factor in factors:
#             if factor > 0:
#                 positive_diff += factor
#             else:
#                 negative_diff += factor

#         sk_score = get_sk_score(certn_score, positive_diff, negative_diff)
    