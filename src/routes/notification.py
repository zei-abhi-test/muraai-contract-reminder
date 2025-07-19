from flask import Blueprint, jsonify, request
from src.services.notification_service import notification_service
from src.models.contract import Contract, Notification

notification_bp = Blueprint('notification', __name__)

@notification_bp.route('/notifications/send-test', methods=['POST'])
def send_test_notification():
    """Send a test notification for a specific contract"""
    try:
        data = request.json
        contract_id = data.get('contract_id')
        notification_type = data.get('type', 'email')  # 'email' or 'mobile'
        
        contract = Contract.query.get_or_404(contract_id)
        
        if notification_type == 'email' and contract.notification_email:
            subject = f"Test Notification - {contract.contract_name}"
            body = notification_service.create_email_template(contract, 7)  # Test with 7 days
            
            success, message = notification_service.send_email_notification(
                contract.notification_email,
                subject,
                body,
                contract.id
            )
            
            return jsonify({
                'success': success,
                'message': message,
                'type': 'email'
            })
        
        elif notification_type == 'mobile':
            # For demo purposes, we'll simulate a push notification
            title = "Test Contract Renewal Reminder"
            body_text = f"This is a test notification for {contract.contract_name}"
            
            # In a real implementation, you would use actual device tokens
            notification = Notification(
                contract_id=contract.id,
                notification_type='mobile',
                status='sent',
                message=f'Test push notification: {body_text}'
            )
            from src.models.contract import db
            db.session.add(notification)
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': 'Test push notification sent successfully',
                'type': 'mobile'
            })
        
        else:
            return jsonify({
                'success': False,
                'message': 'Invalid notification type or missing configuration'
            }), 400
            
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@notification_bp.route('/notifications/check-renewals', methods=['POST'])
def check_renewals():
    """Manually trigger the renewal check and notification process"""
    try:
        results = notification_service.check_and_send_notifications()
        
        return jsonify({
            'success': True,
            'results': results
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@notification_bp.route('/notifications/history/<int:contract_id>', methods=['GET'])
def get_notification_history(contract_id):
    """Get notification history for a specific contract"""
    try:
        notifications = Notification.query.filter_by(contract_id=contract_id).order_by(
            Notification.send_date.desc()
        ).all()
        
        return jsonify([notification.to_dict() for notification in notifications])
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@notification_bp.route('/notifications/settings/<int:contract_id>', methods=['PUT'])
def update_notification_settings(contract_id):
    """Update notification settings for a specific contract"""
    try:
        contract = Contract.query.get_or_404(contract_id)
        data = request.json
        
        if 'notification_enabled' in data:
            contract.notification_enabled = data['notification_enabled']
        if 'notification_email' in data:
            contract.notification_email = data['notification_email']
        if 'notification_mobile' in data:
            contract.notification_mobile = data['notification_mobile']
        
        from src.models.contract import db
        db.session.commit()
        
        return jsonify({
            'success': True,
            'message': 'Notification settings updated successfully',
            'contract': contract.to_dict()
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

@notification_bp.route('/notifications/configure', methods=['POST'])
def configure_notifications():
    """Configure global notification settings"""
    try:
        data = request.json
        
        # This would typically update application configuration
        # For demo purposes, we'll just return success
        
        return jsonify({
            'success': True,
            'message': 'Notification configuration updated',
            'config': data
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        }), 500

