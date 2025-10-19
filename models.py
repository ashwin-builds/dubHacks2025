from datetime import datetime
from typing import List, Optional
from enum import Enum
import google.generativeai as genai
import json


# Configure Gemini API
genai.configure(api_key="AIzaSyCGufO50oWxM03GUm_NuYxXj-PxdzJPoCY")
model = genai.GenerativeModel("gemini-2.0-flash-lite")


import csv
from pathlib import Path

def append_to_csv(file_path: str, data: dict, fieldnames: list):
    """Append a dictionary as a row to a CSV file. Create file with headers if it doesn't exist."""
    file = Path(file_path)
    write_header = not file.exists()
    
    with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if write_header:
            writer.writeheader()
        writer.writerow(data)


class ItemCategory(Enum):
    FOOD = "food"
    CLOTHING = "clothing"
    SHELTER = "shelter"
    MEDICAL = "medical"
    HYGIENE = "hygiene"
    OTHER = "other"

class RequestStatus(Enum):
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FULFILLED = "fulfilled"
    CANCELLED = "cancelled"

class Item:
    """Represents an item that can be requested or donated"""
    def __init__(self, name: str, quantity: int, description: str = "", category: str = ""):
        self.name = name
        self.quantity = quantity
        self.description = description
        # If category is provided, use it; otherwise auto-categorize
        if category:
            self.category = self._string_to_category(category)
        else:
            self.category = self._auto_categorize()
    
    def _string_to_category(self, category_str: str):
        """Convert string to ItemCategory enum"""
        category_str = category_str.lower().strip()
        for category in ItemCategory:
            if category.value == category_str:
                return category
        return ItemCategory.OTHER
    
    def _auto_categorize(self):
        """Use Gemini to automatically categorize items"""
        try:
            prompt = f"""Categorize this item into ONE of these categories: food, clothing, shelter, medical, hygiene, other.
Item: {self.name}
Description: {self.description}

Respond with ONLY the category word, nothing else."""
            
            response = model.generate_content(prompt)
            category_str = response.text.strip().lower()
            
            # Map response to enum
            for category in ItemCategory:
                if category.value == category_str:
                    return category
            return ItemCategory.OTHER
        except:
            return ItemCategory.OTHER
    
    def to_dict(self):
        return {
            'name': self.name,
            'quantity': self.quantity,
            'description': self.description,
            'category': self.category.value
        }
    
    def __str__(self):
        return f"{self.name} ({self.category.value}) - Qty: {self.quantity}"

class TextParser:
    """Parse free-form text into structured Item objects using Gemini AI"""
    
    @staticmethod
    def parse_text_to_items(text: str) -> List[Item]:
        """
        Parse user's free-form text into a list of Item objects
        
        Examples:
        - "I need 10 blankets and 5 cans of soup"
        - "Looking for winter clothes, maybe 3 jackets and some gloves"
        - "We have 20 boxes of food to donate"
        """
        try:
            prompt = f"""You are parsing donation/request text into structured items.

USER TEXT: "{text}"

Extract all items mentioned and return them as a JSON array. For each item:
1. Determine the item name (be specific but concise)
2. Extract or estimate the quantity (default to 1 if not specified)
3. Create a brief description
4. Categorize into either food or shelter

Return ONLY a valid JSON array in this exact format:
[
  {{"name": "Item Name", "quantity": 10, "description": "Brief description", "category": "food"}},
  {{"name": "Another Item", "quantity": 5, "description": "Brief description", "category": "clothing"}}
]

Rules:
- If quantity is vague, use 3-10 as estimate based off key words
- If no quantity mentioned, use 1
- Be specific with item names (e.g., "Winter blankets" not just "blankets")
- Keep descriptions under 15 words
- Return empty array [] if no items found"""

            response = model.generate_content(prompt)
            response_text = response.text.strip()
            
            # Extract JSON from potential markdown code blocks
            if "```json" in response_text:
                response_text = response_text.split("```json")[1].split("```")[0].strip()
            elif "```" in response_text:
                response_text = response_text.split("```")[1].split("```")[0].strip()
            
            # Parse JSON
            items_data = json.loads(response_text)
            
            # Convert to Item objects
            items = []
            for item_data in items_data:
                item = Item(
                    name=item_data.get('name', 'Unknown Item'),
                    quantity=item_data.get('quantity', 1),
                    description=item_data.get('description', ''),
                    category=item_data.get('category', 'other')
                )
                items.append(item)
            
            return items
            
        except Exception as e:
            print(f"Error parsing text: {e}")
            # Fallback: create a single generic item from the text
            return [Item(
                name=text[:50] + "..." if len(text) > 50 else text,
                quantity=1,
                description="Auto-parsed from user input",
                category="other"
            )]
    
    @staticmethod
    def analyze_urgency(text: str) -> str:
        """
        Analyze text to determine urgency level: low, normal, high, urgent
        """
        try:
            prompt = f"""Analyze this text and determine the urgency level.

TEXT: "{text}"

Consider words like: urgent, emergency, ASAP, desperate, critical, immediate, soon, needed
Also consider context like: cold weather, children, elderly, medical needs

Return ONLY one word: low, normal, high, or urgent"""

            response = model.generate_content(prompt)
            urgency = response.text.strip().lower()
            
            if urgency in ['low', 'normal', 'high', 'urgent']:
                return urgency
            return 'normal'
            
        except:
            return 'normal'

class Request:
    """Represents a request for items"""
    CSV_FILE = "requests.csv"
    CSV_FIELDS = ['id', 'requester_id', 'requester_name', 'items', 'urgency', 'status', 'created_at', 'fulfilled_by']

    def __init__(self, requester, items: list, urgency: str = "normal"):
        self.id = id(self)
        self.requester = requester
        self.items = items
        self.urgency = urgency
        self.status = RequestStatus.OPEN
        self.created_at = datetime.now()
        self.fulfilled_by = None
        
        # Log to CSV
        self.log_to_csv()
    
    def fulfill(self, donor):
        """Mark request as fulfilled by a donor"""
        self.status = RequestStatus.FULFILLED
        self.fulfilled_by = donor
        self.log_to_csv()  # Update CSV when fulfilled
        return True
    
    def to_dict(self):
        return {
            'id': self.id,
            'requester_id': self.requester.id,
            'requester_name': self.requester.name,
            'items': "; ".join([f"{item.name} ({item.quantity})" for item in self.items]),
            'urgency': self.urgency,
            'status': self.status.value,
            'created_at': self.created_at.isoformat(),
            'fulfilled_by': self.fulfilled_by.id if self.fulfilled_by else None
        }
    
    def log_to_csv(self):
        append_to_csv(self.CSV_FILE, self.to_dict(), self.CSV_FIELDS)

    
    def __str__(self):
        items_str = ", ".join([str(item) for item in self.items])
        return f"Request #{self.id} by {self.requester.name}: {items_str} [{self.status.value}]"

class Offering:
    """Represents items offered by a donor or shelter"""
    CSV_FILE = "offerings.csv"
    CSV_FIELDS = ['id', 'donor_id', 'donor_name', 'items', 'available', 'created_at']

    def __init__(self, donor, items: list):
        self.id = id(self)
        self.donor = donor
        self.items = items
        self.available = True
        self.created_at = datetime.now()
        
        # Log to CSV
        self.log_to_csv()
    
    def mark_donated(self):
        """Mark offering as no longer available"""
        self.available = False
        self.log_to_csv()  # Update CSV when marked donated
    
    def to_dict(self):
        return {
            'id': self.id,
            'donor_id': self.donor.id,
            'donor_name': self.donor.name,
            'items': "; ".join([f"{item.name} ({item.quantity})" for item in self.items]),
            'available': self.available,
            'created_at': self.created_at.isoformat()
        }
    
    def log_to_csv(self):
        append_to_csv(self.CSV_FILE, self.to_dict(), self.CSV_FIELDS)

    
    def __str__(self):
        items_str = ", ".join([str(item) for item in self.items])
        status = "Available" if self.available else "Donated"
        return f"Offering #{self.id} by {self.donor.name}: {items_str} [{status}]"

class User:
    """Base class for all users in the system"""
    def __init__(self, name: str, location: str, contact: str = ""):
        self.id = id(self)
        self.name = name
        self.location = location
        self.contact = contact
        self.created_at = datetime.now()
    
    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'location': self.location,
            'contact': self.contact,
            'user_type': self.__class__.__name__,
            'created_at': self.created_at.isoformat()
        }
    
    def __str__(self):
        return f"{self.__class__.__name__}: {self.name} ({self.location})"

class Shelter(User):
    """Shelter that can both request and offer items"""
    def __init__(self, name: str, location: str, contact: str = ""):
        super().__init__(name, location, contact)
        self.current_occupancy = 0
        self.requests: List[Request] = []
        self.offerings: List[Offering] = []
    
    def create_request_from_text(self, text: str):
        """Create a request from free-form text"""
        items = TextParser.parse_text_to_items(text)
        urgency = TextParser.analyze_urgency(text)
        request = Request(self, items, urgency)
        self.requests.append(request)
        return request
    
    def create_request(self, items: List[Item], urgency: str = "normal"):
        """Create a request with pre-made items (legacy support)"""
        request = Request(self, items, urgency)
        self.requests.append(request)
        return request
    
    def create_offering_from_text(self, text: str):
        """Create an offering from free-form text"""
        items = TextParser.parse_text_to_items(text)
        offering = Offering(self, items)
        self.offerings.append(offering)
        return offering
    
    def create_offering(self, items: List[Item]):
        """Create an offering with pre-made items (legacy support)"""
        offering = Offering(self, items)
        self.offerings.append(offering)
        return offering
    
    # def get_available_space(self):
    #     """Calculate remaining capacity"""
    #     return self.capacity - self.current_occupancy
    
    def to_dict(self):
        data = super().to_dict()
        data.update({
            'current_occupancy': self.current_occupancy,
            'available_space': self.get_available_space()
        })
        return data

class Donor(User):
    """Donor who can offer items to shelters and requesters"""
    def __init__(self, name: str, location: str, contact: str = ""):
        super().__init__(name, location, contact)
        self.offerings: List[Offering] = []
        self.fulfilled_requests: List[Request] = []
    
    def create_offering_from_text(self, text: str):
        """Create an offering from free-form text"""
        items = TextParser.parse_text_to_items(text)
        offering = Offering(self, items)
        self.offerings.append(offering)
        return offering
    
    def create_offering(self, items: List[Item]):
        """Create an offering with pre-made items (legacy support)"""
        offering = Offering(self, items)
        self.offerings.append(offering)
        return offering
    
    def fulfill_request(self, request: Request):
        """Fulfill a request from a shelter or requester"""
        if request.status == RequestStatus.OPEN:
            request.fulfill(self)
            self.fulfilled_requests.append(request)
            return True
        return False

class Needers(User):
    """Individual in need who can request items"""
    def __init__(self, name: str, location: str, contact: str = ""):
        super().__init__(name, location, contact)
        self.requests: List[Request] = []
    
    def create_request_from_text(self, text: str):
        """Create a request from free-form text"""
        items = TextParser.parse_text_to_items(text)
        urgency = TextParser.analyze_urgency(text)
        request = Request(self, items, urgency)
        self.requests.append(request)
        return request
    
    def create_request(self, items: List[Item], urgency: str = "normal"):
        """Create a request with pre-made items (legacy support)"""
        request = Request(self, items, urgency)
        self.requests.append(request)
        return request

class CoordinationSystem:
    """Main system to coordinate between all users using Gemini AI"""
    def __init__(self):
        self.shelters: List[Shelter] = []
        self.donors: List[Donor] = []
        self.needers: List[Needers] = []
        self.all_requests: List[Request] = []
        self.all_offerings: List[Offering] = []
    
    def register_shelter(self, shelter: Shelter):
        """Register a new shelter"""
        self.shelters.append(shelter)
    
    def register_donor(self, donor: Donor):
        """Register a new donor"""
        self.donors.append(donor)
    
    def register_needer(self, needer: Needers):
        """Register a new needer"""
        self.needers.append(needer)
    
    def add_request(self, request: Request):
        """Add a request to the system"""
        self.all_requests.append(request)
    
    def add_offering(self, offering: Offering):
        """Add an offering to the system"""
        self.all_offerings.append(offering)
    
    def get_open_requests(self, category: Optional[ItemCategory] = None):
        """Get all open requests, optionally filtered by category"""
        open_requests = [r for r in self.all_requests if r.status == RequestStatus.OPEN]
        if category:
            return [r for r in open_requests if any(item.category == category for item in r.items)]
        return open_requests
    
    def get_available_offerings(self, category: Optional[ItemCategory] = None):
        """Get all available offerings, optionally filtered by category"""
        available = [o for o in self.all_offerings if o.available]
        if category:
            return [o for o in available if any(item.category == category for item in o.items)]
        return available
    
    def ai_match_requests_with_offerings(self):
        """Use Gemini AI to intelligently match requests with offerings"""
        open_requests = self.get_open_requests()
        available_offerings = self.get_available_offerings()
        
        if not open_requests or not available_offerings:
            return []
        
        # Build context for Gemini
        requests_info = ""
        for i, req in enumerate(open_requests):
            items = ", ".join([f"{item.name} (qty: {item.quantity})" for item in req.items])
            requests_info += f"{i}. {req.requester.name} in {req.requester.location} needs: {items} [Urgency: {req.urgency}]\n"
        
        offerings_info = ""
        for i, off in enumerate(available_offerings):
            items = ", ".join([f"{item.name} (qty: {item.quantity})" for item in off.items])
            offerings_info += f"{i}. {off.donor.name} in {off.donor.location} offers: {items}\n"
        
        prompt = f"""You are a smart matching system for a donation coordination platform.

REQUESTS:
{requests_info}

OFFERINGS:
{offerings_info}

Analyze these requests and offerings. Find the best matches considering:
1. Item compatibility (similar or matching items)
2. Quantity availability
3. Urgency level (prioritize urgent/high requests)
4. Location proximity

Return matches in this exact format (one per line):
REQUEST_INDEX,OFFERING_INDEX,CONFIDENCE_SCORE,REASON

Example: 0,1,0.9,Exact match on blankets with sufficient quantity and close location

Only return matches with confidence >= 0.5"""
        
        try:
            response = model.generate_content(prompt)
            matches = []
            
            for line in response.text.strip().split('\n'):
                if ',' in line:
                    try:
                        parts = line.split(',', 3)
                        req_idx = int(parts[0].strip())
                        off_idx = int(parts[1].strip())
                        confidence = float(parts[2].strip())
                        reason = parts[3].strip()
                        
                        if req_idx < len(open_requests) and off_idx < len(available_offerings):
                            matches.append({
                                'request': open_requests[req_idx],
                                'offering': available_offerings[off_idx],
                                'confidence': confidence,
                                'reason': reason
                            })
                    except (ValueError, IndexError):
                        continue
            
            return matches
        except Exception as e:
            print(f"AI matching error: {e}")
            return []
    
    def generate_message_suggestion(self, sender: User, recipient: User, context: str):
        """Use Gemini to generate a personalized message between users"""
        prompt = f"""Generate a friendly, professional message for a donation coordination platform.

FROM: {sender.name} ({sender.__class__.__name__})
TO: {recipient.name} ({recipient.__class__.__name__})
CONTEXT: {context}

Write a warm, helpful message (2-3 sentences) that {sender.name} can send to {recipient.name}. Be specific and actionable."""
        
        try:
            response = model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            return f"Hi {recipient.name}, I'd like to connect regarding {context}. Please let me know if you're available to coordinate."


# Example usage
if __name__ == "__main__":
    print("=" * 70)
    print("DONATION COORDINATION SYSTEM - Text-to-Items Parsing Demo")
    print("=" * 70)
    
    # Initialize the system
    system = CoordinationSystem()
    
    # Create users
    shelter1 = Shelter("Hope Shelter", "Downtown Seattle", contact="555-0100")
    donor1 = Donor("John Smith", "Capitol Hill", "555-0200")
    needer1 = Needers("Mary Johnson", "Belltown", "555-0300")
    
    # Register users
    system.register_shelter(shelter1)
    system.register_donor(donor1)
    system.register_needer(needer1)
    
    print("\n=== SHELTER REQUEST (from text) ===")
    shelter_text = "We urgently need 20 warm blankets and about 50 cans of soup for the winter. Also need some hygiene supplies."
    print(f"Input text: \"{shelter_text}\"")
    shelter_request = shelter1.create_request_from_text(shelter_text)
    system.add_request(shelter_request)
    print(f"Parsed items:")
    for item in shelter_request.items:
        print(f"  - {item}")
    print(f"Detected urgency: {shelter_request.urgency}")
    
    print("\n=== DONOR OFFERING (from text) ===")
    donor_text = "I have 25 fleece blankets and 15 winter jackets I'd like to donate"
    print(f"Input text: \"{donor_text}\"")
    donor_offering = donor1.create_offering_from_text(donor_text)
    system.add_offering(donor_offering)
    print(f"Parsed items:")
    for item in donor_offering.items:
        print(f"  - {item}")
    
    print("\n=== NEEDER REQUEST (from text) ===")
    needer_text = "Need groceries for my family of 4 ASAP, especially food for the kids"
    print(f"Input text: \"{needer_text}\"")
    needer_request = needer1.create_request_from_text(needer_text)
    system.add_request(needer_request)
    print(f"Parsed items:")
    for item in needer_request.items:
        print(f"  - {item}")
    print(f"Detected urgency: {needer_request.urgency}")
    
    # Display system status
    print("\n=== ALL OPEN REQUESTS ===")
    for req in system.get_open_requests():
        print(req)
    
    print("\n=== ALL AVAILABLE OFFERINGS ===")
    for off in system.get_available_offerings():
        print(off)
    
    # AI-powered matching
    print("\n=== AI-POWERED MATCHES ===")
    matches = system.ai_match_requests_with_offerings()
    for match in matches:
        print(f"\n✓ Match (Confidence: {match['confidence']}):")
        print(f"  Requester: {match['request'].requester.name}")
        print(f"  Donor: {match['offering'].donor.name}")
        print(f"  Reason: {match['reason']}")
    
    # Generate a message suggestion
    if matches:
        print("\n=== AI-GENERATED MESSAGE ===")
        message = system.generate_message_suggestion(
            matches[0]['offering'].donor,
            matches[0]['request'].requester,
            "your donation matching their urgent need"
        )
        print(f"From: {matches[0]['offering'].donor.name}")
        print(f"To: {matches[0]['request'].requester.name}")
        print(f'Message: "{message}"')
    
    print("\n" + "=" * 70)
    print("Demo complete!")
    print("=" * 70)