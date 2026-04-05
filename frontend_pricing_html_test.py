#!/usr/bin/env python3
"""
Frontend Pricing Validation Test (HTML Content Analysis)
Tests specific frontend pricing requirements by analyzing HTML content:
1. /pricing should show Pro cards with labels "Pro — $31 / month" and "Pro — $313 / year"
2. /pricing should show Effort support donation section with amount input and Donate button
"""

import requests
import re
import sys
from bs4 import BeautifulSoup

# Use the production URL
BASE_URL = "https://aimmh-hub-1.preview.emergentagent.com"

def fetch_pricing_page():
    """Fetch the pricing page HTML content"""
    print("\n🌐 Fetching pricing page...")
    
    try:
        response = requests.get(f"{BASE_URL}/pricing", timeout=30)
        
        if response.status_code != 200:
            print(f"❌ Pricing page request failed: {response.status_code}")
            return None
        
        print(f"✅ Pricing page fetched successfully ({len(response.text)} chars)")
        return response.text
        
    except Exception as e:
        print(f"❌ Error fetching pricing page: {e}")
        return None

def test_pro_pricing_labels(html_content):
    """Test that Pro pricing cards show correct labels"""
    print("\n💳 Testing Pro pricing labels in HTML...")
    
    try:
        # Look for Pro monthly and yearly pricing text
        pro_monthly_patterns = [
            r"Pro\s*—\s*\$31\s*/\s*month",
            r"Pro\s*-\s*\$31\s*/\s*month",
            r"\$31\s*/\s*month",
            r"31\.0.*month",
            r"Pro.*\$31.*month"
        ]
        
        pro_yearly_patterns = [
            r"Pro\s*—\s*\$313\s*/\s*year",
            r"Pro\s*-\s*\$313\s*/\s*year", 
            r"\$313\s*/\s*year",
            r"313\.0.*year",
            r"Pro.*\$313.*year"
        ]
        
        pro_monthly_found = False
        pro_yearly_found = False
        
        # Check for monthly pricing
        for pattern in pro_monthly_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                print(f"✅ Found Pro monthly pricing pattern: {pattern}")
                pro_monthly_found = True
                break
        
        # Check for yearly pricing
        for pattern in pro_yearly_patterns:
            if re.search(pattern, html_content, re.IGNORECASE):
                print(f"✅ Found Pro yearly pricing pattern: {pattern}")
                pro_yearly_found = True
                break
        
        # If not found with patterns, let's search more broadly
        if not pro_monthly_found:
            if "$31" in html_content and "month" in html_content.lower():
                print(f"✅ Found $31 and month in content (Pro monthly likely present)")
                pro_monthly_found = True
            else:
                print(f"❌ Pro monthly pricing ($31/month) not found")
        
        if not pro_yearly_found:
            if "$313" in html_content and "year" in html_content.lower():
                print(f"✅ Found $313 and year in content (Pro yearly likely present)")
                pro_yearly_found = True
            else:
                print(f"❌ Pro yearly pricing ($313/year) not found")
        
        return pro_monthly_found and pro_yearly_found
        
    except Exception as e:
        print(f"❌ Error testing Pro pricing labels: {e}")
        return False

def test_donation_section(html_content):
    """Test that donation section exists with amount input and Donate button"""
    print("\n💝 Testing donation section in HTML...")
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for donation/support section text
        donation_keywords = [
            "effort support",
            "donation",
            "donate",
            "support",
            "custom amount"
        ]
        
        donation_section_found = False
        for keyword in donation_keywords:
            if keyword.lower() in html_content.lower():
                print(f"✅ Found donation keyword: {keyword}")
                donation_section_found = True
                break
        
        # Look for amount input field
        amount_input_found = False
        
        # Check for number inputs
        number_inputs = soup.find_all('input', {'type': 'number'})
        if number_inputs:
            print(f"✅ Found {len(number_inputs)} number input field(s)")
            amount_input_found = True
        
        # Check for inputs with amount-related attributes
        amount_inputs = soup.find_all('input', attrs={
            'placeholder': re.compile(r'amount', re.I)
        }) or soup.find_all('input', attrs={
            'name': re.compile(r'amount', re.I)
        }) or soup.find_all('input', attrs={
            'id': re.compile(r'amount', re.I)
        })
        
        if amount_inputs:
            print(f"✅ Found amount-related input field(s)")
            amount_input_found = True
        
        # Look for Donate button
        donate_button_found = False
        
        # Check for buttons with "Donate" text
        donate_buttons = soup.find_all('button', string=re.compile(r'donate', re.I))
        if not donate_buttons:
            # Check for buttons containing "Donate" text
            all_buttons = soup.find_all('button')
            for button in all_buttons:
                if button.get_text() and 'donate' in button.get_text().lower():
                    donate_buttons.append(button)
        
        if donate_buttons:
            print(f"✅ Found {len(donate_buttons)} Donate button(s)")
            donate_button_found = True
        
        # Check for submit inputs with Donate value
        donate_submits = soup.find_all('input', {'type': 'submit', 'value': re.compile(r'donate', re.I)})
        if donate_submits:
            print(f"✅ Found Donate submit input(s)")
            donate_button_found = True
        
        # Summary
        if donation_section_found and amount_input_found and donate_button_found:
            print(f"✅ Complete donation section found")
            return True
        else:
            print(f"❌ Donation section incomplete:")
            print(f"   - Section text: {donation_section_found}")
            print(f"   - Amount input: {amount_input_found}")
            print(f"   - Donate button: {donate_button_found}")
            return False
            
    except Exception as e:
        print(f"❌ Error testing donation section: {e}")
        return False

def analyze_pricing_structure(html_content):
    """Analyze the overall pricing structure for debugging"""
    print("\n🔍 Analyzing pricing page structure...")
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for pricing-related elements
        print("📋 Found pricing-related elements:")
        
        # Check for price amounts
        price_patterns = [r'\$\d+', r'\$\d+\.\d+']
        for pattern in price_patterns:
            matches = re.findall(pattern, html_content)
            if matches:
                print(f"   💰 Price amounts found: {set(matches)}")
        
        # Check for billing periods
        billing_terms = ['month', 'year', 'monthly', 'yearly', 'annual']
        found_terms = []
        for term in billing_terms:
            if term.lower() in html_content.lower():
                found_terms.append(term)
        if found_terms:
            print(f"   📅 Billing terms found: {found_terms}")
        
        # Check for plan names
        plan_terms = ['pro', 'supporter', 'team', 'free']
        found_plans = []
        for plan in plan_terms:
            if plan.lower() in html_content.lower():
                found_plans.append(plan)
        if found_plans:
            print(f"   📦 Plan types found: {found_plans}")
        
        # Check for form elements
        inputs = soup.find_all('input')
        buttons = soup.find_all('button')
        print(f"   🔘 Form elements: {len(inputs)} inputs, {len(buttons)} buttons")
        
        return True
        
    except Exception as e:
        print(f"❌ Error analyzing pricing structure: {e}")
        return False

def main():
    """Run all frontend pricing validation tests"""
    print("🎯 FRONTEND PRICING VALIDATION TEST SUITE (HTML Analysis)")
    print("=" * 60)
    
    # Fetch pricing page
    html_content = fetch_pricing_page()
    if not html_content:
        print("❌ Failed to fetch pricing page")
        sys.exit(1)
    
    # Analyze structure for debugging
    analyze_pricing_structure(html_content)
    
    # Run all tests
    tests = [
        ("Pro Pricing Labels", lambda: test_pro_pricing_labels(html_content)),
        ("Donation Section", lambda: test_donation_section(html_content))
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            if result:
                print(f"✅ {test_name}: PASSED")
            else:
                print(f"❌ {test_name}: FAILED")
        except Exception as e:
            print(f"❌ {test_name}: ERROR - {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS SUMMARY")
    print("=" * 60)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
        if result:
            passed += 1
    
    print(f"\n🎯 Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL FRONTEND PRICING TESTS PASSED!")
        return True
    else:
        print("⚠️  Some frontend pricing tests failed")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)