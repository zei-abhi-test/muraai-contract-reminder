from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
import atexit
import logging
from src.services.notification_service import notification_service

class SchedulerService:
    def __init__(self, app=None):
        self.scheduler = None
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        self.app = app
        self.scheduler = BackgroundScheduler()
        
        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger(__name__)
        
        # Schedule daily notification check at 9:00 AM
        self.scheduler.add_job(
            func=self.check_and_send_notifications,
            trigger=CronTrigger(hour=9, minute=0),  # Daily at 9:00 AM
            id='daily_notification_check',
            name='Daily Contract Renewal Notification Check',
            replace_existing=True
        )
        
        # Schedule weekly summary on Mondays at 8:00 AM
        self.scheduler.add_job(
            func=self.send_weekly_summary,
            trigger=CronTrigger(day_of_week='mon', hour=8, minute=0),  # Weekly on Monday at 8:00 AM
            id='weekly_summary',
            name='Weekly Contract Summary',
            replace_existing=True
        )
        
        # Start the scheduler
        self.scheduler.start()
        self.logger.info("Scheduler started successfully")
        
        # Shut down the scheduler when exiting the app
        atexit.register(lambda: self.scheduler.shutdown())
    
    def check_and_send_notifications(self):
        """Job function to check for contract renewals and send notifications"""
        try:
            with self.app.app_context():
                self.logger.info("Starting daily notification check...")
                results = notification_service.check_and_send_notifications()
                
                self.logger.info(f"Notification check completed: {results['emails_sent']} emails sent, "
                               f"{results['push_notifications_sent']} push notifications sent")
                
                if results['errors']:
                    self.logger.error(f"Errors during notification check: {results['errors']}")
                
                return results
        except Exception as e:
            self.logger.error(f"Error during scheduled notification check: {str(e)}")
            return {'error': str(e)}
    
    def send_weekly_summary(self):
        """Job function to send weekly summary of upcoming renewals"""
        try:
            with self.app.app_context():
                from src.models.contract import Contract
                from datetime import datetime, timedelta
                
                self.logger.info("Starting weekly summary...")
                
                # Get contracts due in the next 7 days
                today = datetime.now().date()
                next_week = today + timedelta(days=7)
                
                upcoming_contracts = Contract.query.filter(
                    Contract.renewal_date >= today,
                    Contract.renewal_date <= next_week,
                    Contract.notification_enabled == True
                ).all()
                
                if upcoming_contracts:
                    # Group contracts by user email
                    user_contracts = {}
                    for contract in upcoming_contracts:
                        if contract.notification_email:
                            if contract.notification_email not in user_contracts:
                                user_contracts[contract.notification_email] = []
                            user_contracts[contract.notification_email].append(contract)
                    
                    # Send summary emails
                    for email, contracts in user_contracts.items():
                        subject = f"Weekly Contract Renewal Summary - {len(contracts)} contracts due"
                        body = self.create_weekly_summary_template(contracts)
                        
                        success, message = notification_service.send_email_notification(
                            email, subject, body
                        )
                        
                        if success:
                            self.logger.info(f"Weekly summary sent to {email}")
                        else:
                            self.logger.error(f"Failed to send weekly summary to {email}: {message}")
                
                self.logger.info("Weekly summary completed")
                
        except Exception as e:
            self.logger.error(f"Error during weekly summary: {str(e)}")
    
    def create_weekly_summary_template(self, contracts):
        """Create HTML template for weekly summary email"""
        contract_rows = ""
        for contract in contracts:
            days_until = (contract.renewal_date - datetime.now().date()).days
            urgency_color = "#dc2626" if days_until <= 3 else "#f59e0b" if days_until <= 7 else "#3b82f6"
            
            contract_rows += f"""
            <tr style="border-bottom: 1px solid #e2e8f0;">
                <td style="padding: 12px; font-weight: bold;">{contract.contract_name}</td>
                <td style="padding: 12px;">{contract.company_name}</td>
                <td style="padding: 12px;">{contract.renewal_date.strftime('%B %d, %Y')}</td>
                <td style="padding: 12px; color: {urgency_color}; font-weight: bold;">{days_until} days</td>
            </tr>
            """
        
        html_template = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Weekly Contract Summary</title>
        </head>
        <body style="font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px;">
            <div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); padding: 30px; text-align: center; border-radius: 10px 10px 0 0;">
                <h1 style="color: white; margin: 0; font-size: 28px;">Muraai Contract Manager</h1>
                <p style="color: #e2e8f0; margin: 10px 0 0 0;">Weekly Contract Summary</p>
            </div>
            
            <div style="background: white; padding: 30px; border: 1px solid #e2e8f0; border-top: none;">
                <h2 style="color: #1f2937; margin: 0 0 20px 0;">Contracts Due This Week</h2>
                <p style="margin-bottom: 25px;">You have {len(contracts)} contracts due for renewal in the next 7 days:</p>
                
                <table style="width: 100%; border-collapse: collapse; margin: 20px 0;">
                    <thead>
                        <tr style="background: #f8fafc;">
                            <th style="padding: 12px; text-align: left; font-weight: bold; border-bottom: 2px solid #e2e8f0;">Contract</th>
                            <th style="padding: 12px; text-align: left; font-weight: bold; border-bottom: 2px solid #e2e8f0;">Company</th>
                            <th style="padding: 12px; text-align: left; font-weight: bold; border-bottom: 2px solid #e2e8f0;">Renewal Date</th>
                            <th style="padding: 12px; text-align: left; font-weight: bold; border-bottom: 2px solid #e2e8f0;">Days Left</th>
                        </tr>
                    </thead>
                    <tbody>
                        {contract_rows}
                    </tbody>
                </table>
                
                <div style="background: #fef3c7; border: 1px solid #f59e0b; padding: 15px; border-radius: 8px; margin: 25px 0;">
                    <p style="margin: 0; color: #92400e;"><strong>Reminder:</strong> Review these contracts and take necessary action to ensure continuity of your services.</p>
                </div>
                
                <div style="text-align: center; margin: 30px 0;">
                    <a href="#" style="background: #3b82f6; color: white; padding: 12px 24px; text-decoration: none; border-radius: 6px; display: inline-block; font-weight: bold;">Manage Contracts</a>
                </div>
            </div>
            
            <div style="background: #f8fafc; padding: 20px; text-align: center; border-radius: 0 0 10px 10px; border: 1px solid #e2e8f0; border-top: none;">
                <p style="margin: 0; color: #6b7280; font-size: 14px;">
                    This is an automated weekly summary from Muraai Contract Manager.<br>
                    To stop receiving these notifications, please update your notification settings.
                </p>
            </div>
        </body>
        </html>
        """
        
        return html_template
    
    def add_custom_job(self, func, trigger, job_id, name):
        """Add a custom scheduled job"""
        try:
            self.scheduler.add_job(
                func=func,
                trigger=trigger,
                id=job_id,
                name=name,
                replace_existing=True
            )
            self.logger.info(f"Custom job '{name}' added successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to add custom job '{name}': {str(e)}")
            return False
    
    def remove_job(self, job_id):
        """Remove a scheduled job"""
        try:
            self.scheduler.remove_job(job_id)
            self.logger.info(f"Job '{job_id}' removed successfully")
            return True
        except Exception as e:
            self.logger.error(f"Failed to remove job '{job_id}': {str(e)}")
            return False
    
    def get_jobs(self):
        """Get list of all scheduled jobs"""
        jobs = []
        for job in self.scheduler.get_jobs():
            jobs.append({
                'id': job.id,
                'name': job.name,
                'next_run_time': job.next_run_time.isoformat() if job.next_run_time else None,
                'trigger': str(job.trigger)
            })
        return jobs

# Initialize the scheduler service
scheduler_service = SchedulerService()

