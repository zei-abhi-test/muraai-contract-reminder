from flask import Blueprint, jsonify, request
from datetime import datetime, date
from src.models.contract import Contract, Notification, db

contract_bp = Blueprint('contract', __name__)

@contract_bp.route('/contracts', methods=['GET'])
def get_contracts():
    """Get all contracts with optional filtering"""
    user_id = request.args.get('user_id', type=int)
    upcoming_only = request.args.get('upcoming_only', 'false').lower() == 'true'
    
    query = Contract.query
    
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    if upcoming_only:
        # Get contracts with renewal dates in the next 30 days
        from datetime import timedelta
        thirty_days_from_now = date.today() + timedelta(days=30)
        query = query.filter(Contract.renewal_date <= thirty_days_from_now)
    
    contracts = query.order_by(Contract.renewal_date.asc()).all()
    return jsonify([contract.to_dict() for contract in contracts])

@contract_bp.route('/contracts', methods=['POST'])
def create_contract():
    """Create a new contract"""
    try:
        data = request.json
        
        # Parse dates
        start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        renewal_date = datetime.strptime(data['renewal_date'], '%Y-%m-%d').date()
        
        contract = Contract(
            company_name=data['company_name'],
            contract_name=data['contract_name'],
            start_date=start_date,
            end_date=end_date,
            renewal_date=renewal_date,
            notification_enabled=data.get('notification_enabled', True),
            notification_email=data.get('notification_email'),
            notification_mobile=data.get('notification_mobile', False),
            notes=data.get('notes'),
            user_id=data['user_id']
        )
        
        db.session.add(contract)
        db.session.commit()
        return jsonify(contract.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@contract_bp.route('/contracts/<int:contract_id>', methods=['GET'])
def get_contract(contract_id):
    """Get a specific contract by ID"""
    contract = Contract.query.get_or_404(contract_id)
    return jsonify(contract.to_dict())

@contract_bp.route('/contracts/<int:contract_id>', methods=['PUT'])
def update_contract(contract_id):
    """Update a specific contract"""
    try:
        contract = Contract.query.get_or_404(contract_id)
        data = request.json
        
        # Update fields if provided
        if 'company_name' in data:
            contract.company_name = data['company_name']
        if 'contract_name' in data:
            contract.contract_name = data['contract_name']
        if 'start_date' in data:
            contract.start_date = datetime.strptime(data['start_date'], '%Y-%m-%d').date()
        if 'end_date' in data:
            contract.end_date = datetime.strptime(data['end_date'], '%Y-%m-%d').date()
        if 'renewal_date' in data:
            contract.renewal_date = datetime.strptime(data['renewal_date'], '%Y-%m-%d').date()
        if 'notification_enabled' in data:
            contract.notification_enabled = data['notification_enabled']
        if 'notification_email' in data:
            contract.notification_email = data['notification_email']
        if 'notification_mobile' in data:
            contract.notification_mobile = data['notification_mobile']
        if 'notes' in data:
            contract.notes = data['notes']
        
        contract.updated_at = datetime.utcnow()
        db.session.commit()
        return jsonify(contract.to_dict())
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

@contract_bp.route('/contracts/<int:contract_id>', methods=['DELETE'])
def delete_contract(contract_id):
    """Delete a specific contract"""
    contract = Contract.query.get_or_404(contract_id)
    db.session.delete(contract)
    db.session.commit()
    return '', 204

@contract_bp.route('/contracts/dashboard', methods=['GET'])
def get_dashboard_data():
    """Get dashboard data including upcoming renewals and statistics"""
    user_id = request.args.get('user_id', type=int)
    
    query = Contract.query
    if user_id:
        query = query.filter_by(user_id=user_id)
    
    # Get upcoming renewals (next 30 days)
    from datetime import timedelta
    today = date.today()
    thirty_days_from_now = today + timedelta(days=30)
    
    upcoming_contracts = query.filter(
        Contract.renewal_date >= today,
        Contract.renewal_date <= thirty_days_from_now
    ).order_by(Contract.renewal_date.asc()).all()
    
    # Get overdue contracts
    overdue_contracts = query.filter(Contract.renewal_date < today).all()
    
    # Get total contracts
    total_contracts = query.count()
    
    return jsonify({
        'upcoming_renewals': [contract.to_dict() for contract in upcoming_contracts],
        'overdue_contracts': [contract.to_dict() for contract in overdue_contracts],
        'total_contracts': total_contracts,
        'upcoming_count': len(upcoming_contracts),
        'overdue_count': len(overdue_contracts)
    })

@contract_bp.route('/notifications', methods=['GET'])
def get_notifications():
    """Get notification history"""
    contract_id = request.args.get('contract_id', type=int)
    
    query = Notification.query
    if contract_id:
        query = query.filter_by(contract_id=contract_id)
    
    notifications = query.order_by(Notification.send_date.desc()).all()
    return jsonify([notification.to_dict() for notification in notifications])

@contract_bp.route('/notifications', methods=['POST'])
def create_notification():
    """Create a new notification record"""
    try:
        data = request.json
        
        notification = Notification(
            contract_id=data['contract_id'],
            notification_type=data['notification_type'],
            status=data.get('status', 'pending'),
            message=data.get('message')
        )
        
        db.session.add(notification)
        db.session.commit()
        return jsonify(notification.to_dict()), 201
        
    except Exception as e:
        return jsonify({'error': str(e)}), 400

