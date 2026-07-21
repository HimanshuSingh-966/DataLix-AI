"""
Example datasets for demonstration purposes
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import io

def get_sales_dataset() -> bytes:
    """Generate a realistic sales dataset"""
    np.random.seed(42)
    
    n_rows = 500
    
    # Generate dates
    start_date = datetime(2024, 1, 1)
    dates = [start_date + timedelta(days=i) for i in range(n_rows)]
    
    # Product categories and names
    categories = ['Electronics', 'Clothing', 'Food', 'Books', 'Home']
    products = {
        'Electronics': ['Laptop', 'Phone', 'Tablet', 'Headphones', 'Monitor'],
        'Clothing': ['Shirt', 'Pants', 'Shoes', 'Jacket', 'Hat'],
        'Food': ['Coffee', 'Snacks', 'Beverages', 'Meal Kit', 'Dessert'],
        'Books': ['Fiction', 'Non-Fiction', 'Textbook', 'Magazine', 'Comic'],
        'Home': ['Furniture', 'Decor', 'Kitchen', 'Bedding', 'Lighting']
    }
    
    data = []
    for i in range(n_rows):
        category = np.random.choice(categories)
        product = np.random.choice(products[category])
        
        # Generate realistic prices based on category
        base_prices = {
            'Electronics': (200, 2000),
            'Clothing': (20, 150),
            'Food': (5, 50),
            'Books': (10, 80),
            'Home': (30, 500)
        }
        
        min_price, max_price = base_prices[category]
        price = round(np.random.uniform(min_price, max_price), 2)
        
        # Quantity sold
        quantity = int(np.random.exponential(5) + 1)
        
        # Customer satisfaction (1-5 stars)
        satisfaction = int(np.random.normal(4, 0.8))
        satisfaction = max(1, min(5, satisfaction))
        
        # Revenue
        revenue = round(price * quantity, 2)
        
        # Customer age groups
        age_group = np.random.choice(['18-24', '25-34', '35-44', '45-54', '55+'], 
                                    p=[0.15, 0.30, 0.25, 0.20, 0.10])
        
        # Region
        region = np.random.choice(['North', 'South', 'East', 'West'])
        
        # Payment method
        payment = np.random.choice(['Credit Card', 'Debit Card', 'PayPal', 'Cash'], 
                                   p=[0.4, 0.3, 0.2, 0.1])
        
        # Add some missing values (5% chance)
        if np.random.random() < 0.05:
            satisfaction = None
        if np.random.random() < 0.03:
            age_group = None
        
        # Add some outliers (2% chance of very high quantity)
        if np.random.random() < 0.02:
            quantity = int(np.random.uniform(50, 100))
            revenue = round(price * quantity, 2)
        
        data.append({
            'Order_ID': f'ORD-{i+1000:05d}',
            'Date': dates[i].strftime('%Y-%m-%d'),
            'Category': category,
            'Product': product,
            'Price': price,
            'Quantity': quantity,
            'Revenue': revenue,
            'Customer_Age_Group': age_group,
            'Region': region,
            'Payment_Method': payment,
            'Satisfaction_Rating': satisfaction
        })
    
    df = pd.DataFrame(data)
    
    # Convert to CSV bytes
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def get_customer_dataset() -> bytes:
    """Generate a customer analytics dataset"""
    np.random.seed(123)
    
    n_rows = 300
    
    data = []
    for i in range(n_rows):
        # Customer demographics
        age = int(np.random.normal(35, 12))
        age = max(18, min(75, age))
        
        gender = np.random.choice(['Male', 'Female', 'Other'], p=[0.48, 0.48, 0.04])
        
        # Spending patterns
        monthly_spend = round(np.random.gamma(5, 100), 2)
        
        # Customer tenure (months)
        tenure = int(np.random.exponential(24))
        tenure = max(1, min(120, tenure))
        
        # Engagement metrics
        website_visits = int(np.random.poisson(8))
        purchases = int(np.random.poisson(2))
        
        # Customer segment (derived from spending and tenure)
        if monthly_spend > 500 and tenure > 12:
            segment = 'Premium'
        elif monthly_spend > 200:
            segment = 'Regular'
        else:
            segment = 'Occasional'
        
        # Churn risk (higher for low engagement)
        churn_score = round(max(0, min(1, 1 - (website_visits + purchases) / 20)), 2)
        
        # Add some duplicates (3% chance)
        if np.random.random() < 0.03 and i > 0:
            # Copy previous customer
            data.append(data[-1].copy())
            data[-1]['Customer_ID'] = f'CUST-{i+1:05d}'
        else:
            data.append({
                'Customer_ID': f'CUST-{i+1:05d}',
                'Age': age,
                'Gender': gender,
                'Monthly_Spend': monthly_spend,
                'Tenure_Months': tenure,
                'Website_Visits': website_visits,
                'Monthly_Purchases': purchases,
                'Segment': segment,
                'Churn_Risk': churn_score
            })
    
    df = pd.DataFrame(data)
    
    # Convert to CSV bytes
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

def get_employee_dataset() -> bytes:
    """Generate an HR employee dataset"""
    np.random.seed(789)
    
    n_rows = 200
    
    departments = ['Engineering', 'Sales', 'Marketing', 'HR', 'Finance', 'Operations']
    positions = {
        'Engineering': ['Software Engineer', 'Senior Engineer', 'Tech Lead', 'Manager'],
        'Sales': ['Sales Rep', 'Account Manager', 'Sales Director'],
        'Marketing': ['Marketing Specialist', 'Content Creator', 'Marketing Manager'],
        'HR': ['HR Specialist', 'Recruiter', 'HR Manager'],
        'Finance': ['Accountant', 'Financial Analyst', 'Finance Manager'],
        'Operations': ['Operations Specialist', 'Project Manager', 'Operations Director']
    }
    
    data = []
    for i in range(n_rows):
        department = np.random.choice(departments)
        position = np.random.choice(positions[department])
        
        # Salary based on position
        base_salaries = {
            'Specialist': 50000, 'Engineer': 80000, 'Rep': 45000,
            'Manager': 100000, 'Director': 150000, 'Lead': 120000,
            'Analyst': 65000, 'Recruiter': 55000, 'Accountant': 60000,
            'Creator': 50000
        }
        
        base = next((v for k, v in base_salaries.items() if k in position), 60000)
        salary = int(np.random.normal(base, base * 0.2))
        
        # Years of experience
        experience = int(np.random.gamma(2, 2))
        experience = max(0, min(25, experience))
        
        # Performance rating (1-5)
        performance = round(np.random.normal(3.5, 0.8), 1)
        performance = max(1.0, min(5.0, performance))
        
        # Training hours
        training = int(np.random.exponential(20))
        
        # Remote work days per week
        remote_days = np.random.choice([0, 1, 2, 3, 5], p=[0.1, 0.2, 0.3, 0.2, 0.2])
        
        data.append({
            'Employee_ID': f'EMP-{i+1:04d}',
            'Department': department,
            'Position': position,
            'Salary': salary,
            'Years_Experience': experience,
            'Performance_Rating': performance,
            'Training_Hours': training,
            'Remote_Days_Per_Week': remote_days
        })
    
    df = pd.DataFrame(data)
    
    # Convert to CSV bytes
    csv_buffer = io.BytesIO()
    df.to_csv(csv_buffer, index=False)
    csv_buffer.seek(0)
    return csv_buffer.getvalue()

# Available datasets
EXAMPLE_DATASETS = {
    'sales': {
        'name': 'E-Commerce Sales Data',
        'description': '500 sales transactions with revenue, categories, and customer satisfaction',
        'rows': 500,
        'columns': 11,
        'generator': get_sales_dataset
    },
    'customers': {
        'name': 'Customer Analytics',
        'description': '300 customer profiles with spending patterns and churn risk',
        'rows': 300,
        'columns': 9,
        'generator': get_customer_dataset
    },
    'employees': {
        'name': 'HR Employee Data',
        'description': '200 employee records with salaries, performance, and department info',
        'rows': 200,
        'columns': 8,
        'generator': get_employee_dataset
    }
}

def get_example_dataset(dataset_id: str) -> bytes:
    """Get example dataset by ID"""
    if dataset_id not in EXAMPLE_DATASETS:
        raise ValueError(f"Unknown dataset: {dataset_id}")
    
    return EXAMPLE_DATASETS[dataset_id]['generator']()

def list_example_datasets():
    """List all available example datasets"""
    return [
        {
            'id': key,
            'name': info['name'],
            'description': info['description'],
            'rows': info['rows'],
            'columns': info['columns']
        }
        for key, info in EXAMPLE_DATASETS.items()
    ]
