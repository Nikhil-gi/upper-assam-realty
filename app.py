from flask import Flask, render_template, request, jsonify, redirect, url_for
from flask_mail import Mail, Message
from datetime import datetime
import json
import os

from flask import Flask, render_template

app = Flask(__name__)

properties = [
    {
        "title": "Luxury Villa",
        "location": "Dibrugarh",
        "price": "85,00,000",
        "image": "https://images.unsplash.com/photo-1564013799919-ab600027ffc6"
    }
]

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/properties')
def property_page():
    return render_template(
        'properties.html',
        properties=properties
    )

@app.route('/contact')
def contact():
    return render_template('contact.html')

if __name__ == "__main__":
    app.run(debug=True)

app = Flask(__name__)
 
# ── CONFIG ──────────────────────────────────────────────────────────
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'change-this-in-production')
 
# Email config (set these as environment variables in production)
app.config['MAIL_SERVER']   = os.environ.get('MAIL_SERVER', 'smtp.gmail.com')
app.config['MAIL_PORT']     = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS']  = True
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME', '')   # your Gmail
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD', '')   # app password
app.config['MAIL_DEFAULT_SENDER'] = os.environ.get('MAIL_USERNAME', 'hello@upperassamrealty.com')
 
mail = Mail(app)
 
# ── DATA (flat-file JSON, no database needed for v1) ─────────────────
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
 
def load_json(filename):
    path = os.path.join(DATA_DIR, filename)
    if not os.path.exists(path):
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)
 
def save_enquiry(data):
    path = os.path.join(DATA_DIR, 'enquiries.json')
    enquiries = load_json('enquiries.json')
    data['id']         = len(enquiries) + 1
    data['timestamp']  = datetime.now().isoformat()
    data['status']     = 'new'
    enquiries.append(data)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(enquiries, f, indent=2, ensure_ascii=False)
    return data
 
# ── ROUTES ──────────────────────────────────────────────────────────
 
@app.route('/')
def index():
    properties  = load_json('properties.json')
    testimonials = load_json('testimonials.json')
    featured    = [p for p in properties if p.get('featured')][:6]
    return render_template('index.html',
                           properties=featured,
                           testimonials=testimonials)
 
@app.route('/properties')
def properties():
    all_props = load_json('properties.json')
 
    # Filters from query string
    location   = request.args.get('location', '')
    prop_type  = request.args.get('type', '')
    purpose    = request.args.get('purpose', '')   # buy / rent
    budget_max = request.args.get('budget', '')
 
    if location:
        all_props = [p for p in all_props if location.lower() in p.get('location', '').lower()]
    if prop_type:
        all_props = [p for p in all_props if prop_type.lower() in p.get('type', '').lower()]
    if purpose:
        all_props = [p for p in all_props if p.get('purpose', '').lower() == purpose.lower()]
    if budget_max:
        try:
            cap = int(budget_max)
            all_props = [p for p in all_props if int(p.get('price_value', 0)) <= cap]
        except ValueError:
            pass
 
    return render_template('properties.html', properties=all_props,
                           filters={'location': location, 'type': prop_type,
                                    'purpose': purpose, 'budget': budget_max})
 
@app.route('/property/<int:prop_id>')
def property_detail(prop_id):
    all_props = load_json('properties.json')
    prop = next((p for p in all_props if p['id'] == prop_id), None)
    if not prop:
        return redirect(url_for('properties'))
    related = [p for p in all_props if p['id'] != prop_id
               and p.get('location') == prop.get('location')][:3]
    return render_template('property_detail.html', prop=prop, related=related)
 
@app.route('/about')
def about():
    return render_template('about.html')
 
@app.route('/contact')
def contact():
    return render_template('contact.html')
 
@app.route('/video-tours')
def video_tours():
    properties = [p for p in load_json('properties.json') if p.get('video_url')]
    return render_template('video_tours.html', properties=properties)
 
# ── API ROUTES ───────────────────────────────────────────────────────
 
@app.route('/api/enquiry', methods=['POST'])
def submit_enquiry():
    """Handles contact form submission."""
    data = request.get_json()
 
    # Basic validation
    required = ['name', 'phone', 'intent']
    for field in required:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
 
    # Save to JSON file
    enquiry = save_enquiry({
        'name':     data.get('name', '').strip(),
        'phone':    data.get('phone', '').strip(),
        'email':    data.get('email', '').strip(),
        'intent':   data.get('intent', '').strip(),
        'location': data.get('location', '').strip(),
        'message':  data.get('message', '').strip(),
    })
 
    # Send email notification if mail is configured
    if app.config['MAIL_USERNAME']:
        try:
            msg = Message(
                subject=f"New Enquiry #{enquiry['id']} — {enquiry['intent']}",
                recipients=[app.config['MAIL_USERNAME']],
                body=f"""
New enquiry received on Upper Assam Realty website.
 
Name    : {enquiry['name']}
Phone   : {enquiry['phone']}
Email   : {enquiry['email']}
Intent  : {enquiry['intent']}
Location: {enquiry['location']}
Message : {enquiry['message']}
 
Time    : {enquiry['timestamp']}
                """.strip()
            )
            mail.send(msg)
        except Exception as e:
            # Don't fail the request if email fails
            app.logger.warning(f"Email send failed: {e}")
 
    return jsonify({'success': True, 'id': enquiry['id']})
 
@app.route('/api/properties')
def api_properties():
    """JSON endpoint for property search (used by frontend filter)."""
    props = load_json('properties.json')
    return jsonify(props)
 
@app.route('/api/enquiries')
def api_enquiries():
    """Simple admin view — protect this with a password in production."""
    secret = request.args.get('secret', '')
    if secret != os.environ.get('ADMIN_SECRET', 'changeme'):
        return jsonify({'error': 'Unauthorized'}), 401
    return jsonify(load_json('enquiries.json'))
 
# ── TEMPLATE FILTERS ─────────────────────────────────────────────────
 
@app.template_filter('format_price')
def format_price(value):
    """Converts 6800000 → ₹68 Lakh"""
    try:
        n = int(value)
        if n >= 10_000_000:
            return f"₹{n/10_000_000:.2g} Crore"
        elif n >= 100_000:
            return f"₹{n/100_000:.0f} Lakh"
        else:
            return f"₹{n:,}"
    except (ValueError, TypeError):
        return str(value)
 
@app.template_filter('timeago')
def timeago(dt_str):
    try:
        dt = datetime.fromisoformat(dt_str)
        diff = datetime.now() - dt
        if diff.days > 0:
            return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
        hours = diff.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago" if hours else "Just now"
    except Exception:
        return dt_str
 
# ── RUN ──────────────────────────────────────────────────────────────
 
if __name__ == '__main__':
    # Ensure data directory exists
    os.makedirs(DATA_DIR, exist_ok=True)
    # Ensure enquiries file exists
    if not os.path.exists(os.path.join(DATA_DIR, 'enquiries.json')):
        with open(os.path.join(DATA_DIR, 'enquiries.json'), 'w') as f:
            json.dump([], f)
    app.run(debug=True, host='0.0.0.0', port=5000)
 