import re

class NLParser:
    def parse(self, message: str) -> dict:
        msg_lower = message.lower()
        
        intent = "general_query"
        domain = None
        
        if any(w in msg_lower for w in ['visa', 'schengen', 'travel', 'trip', 'europe']):
            domain = "schengen_visa"
        elif any(w in msg_lower for w in ['loan', 'home loan', 'mortgage', 'housing']):
            domain = "home_loan"
        elif any(w in msg_lower for w in ['gst', 'tax', 'registration', 'freelance', 'business']):
            domain = "gst_registration"
            
        if any(w in msg_lower for w in ['status', 'check status', 'track my', 'track status']):
            intent = "check_status"
        elif any(w in msg_lower for w in ['upload', 'submit document', 'add document']):
            intent = "upload_document"
        elif any(w in msg_lower for w in ['list', 'show documents', 'my documents', 'vault']):
            intent = "list_documents"
        elif any(w in msg_lower for w in ['submit application', 'file application', 'apply now', 'submit my']):
            intent = "submit_application"
        elif domain:
            intent = "requirements"
            
        entities = {}
        confidence = 0
        
        # Countries
        countries_list = ['france', 'italy', 'germany', 'spain', 'netherlands', 'switzerland', 'greece', 'portugal', 'austria']
        found_countries = [c.capitalize() for c in countries_list if c in msg_lower]
        if found_countries:
            entities['countries'] = found_countries
            entities['countries_count'] = len(found_countries)
            confidence += 1
            
        # Duration
        duration_match = re.search(r'(\d+)\s*(week|day|month)s?', msg_lower)
        if duration_match:
            val = int(duration_match.group(1))
            unit = duration_match.group(2)
            if unit == 'week':
                duration_days = val * 7
            elif unit == 'month':
                duration_days = val * 30
            else:
                duration_days = val
            entities['duration_days'] = duration_days
            entities['trip_duration'] = duration_days
            confidence += 1
            
        # Income / Salary Extraction
        income_match = re.search(r'(?:earn|income|salary|make)(?:\s+(?:of|is|around))?\s*(?:₹|rs\.?|inr)?\s*([\d,.]+)\s*(lakh|crore|lakhs|crores|k)?', msg_lower)
        if not income_match:
            income_match = re.search(r'([\d,.]+)\s*(lakh|crore|lakhs|crores|k)?\s*(?:per|/|a)\s*month', msg_lower)
            
        if income_match:
            val_str = income_match.group(1).replace(',', '')
            try:
                val = float(val_str)
                unit = income_match.group(2)
                if unit in ['lakh', 'lakhs']:
                    val *= 100000
                elif unit in ['crore', 'crores']:
                    val *= 10000000
                elif unit == 'k':
                    val *= 1000
                entities['income'] = val
                entities['monthly_income'] = val
                confidence += 1
            except ValueError:
                pass

        # Loan or general amount
        loan_amount_match = re.search(r'(?:loan(?:\s+of)?|amount(?:\s+of)?|for)\s*(?:₹|rs\.?|inr)?\s*([\d,.]+)\s*(lakh|crore|lakhs|crores|k)?', msg_lower)
        if not loan_amount_match:
            loan_amount_match = re.search(r'(?:₹|rs\.?|inr)\s*([\d,.]+)\s*(lakh|crore|lakhs|crores|k)?', msg_lower)
        if not loan_amount_match and 'income' not in entities:
            loan_amount_match = re.search(r'([\d,.]+)\s*(lakh|crore|lakhs|crores)?', msg_lower)
            
        if loan_amount_match:
            val_str = loan_amount_match.group(1).replace(',', '')
            try:
                val = float(val_str)
                unit = loan_amount_match.group(2)
                if unit in ['lakh', 'lakhs']:
                    val *= 100000
                elif unit in ['crore', 'crores']:
                    val *= 10000000
                elif unit == 'k':
                    val *= 1000
                entities['amount'] = val
                entities['loan_amount'] = val
                confidence += 1
            except ValueError:
                pass
                
        # Months
        months = ['january', 'february', 'march', 'april', 'may', 'june', 'july', 'august', 'september', 'october', 'november', 'december']
        found_months = [m.capitalize() for m in months if m in msg_lower]
        if found_months:
            entities['months'] = found_months
            entities['month'] = found_months[0]
            confidence += 1
            
        # Employment type
        emp_match = re.search(r'(salaried|self[\s_-]?employed|freelancer)', msg_lower)
        if emp_match:
            entities['employment_type'] = emp_match.group(1).replace('-', '_').replace(' ', '_')
            confidence += 1
            
        # Business type
        biz_match = re.search(r'(company|partnership|proprietorship|freelancer)', msg_lower)
        if biz_match:
            entities['business_type'] = biz_match.group(1)
            confidence += 1
            
        return {
            "intent": intent,
            "domain": domain,
            "entities": entities,
            "confidence": confidence,
            "raw_message": message
        }
