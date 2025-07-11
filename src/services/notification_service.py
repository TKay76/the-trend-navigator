"""Notification service for trend alerts and reports"""

import asyncio
import logging
import json
import httpx
import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Dict, Any, Optional
from datetime import datetime

from .trend_detector import TrendAlert
from ..core.settings import get_settings
from ..core.logging import get_logger

logger = get_logger(__name__)


class NotificationService:
    """
    Multi-channel notification service for trend alerts.
    
    Supports email, Slack, Discord, and other notification channels.
    """
    
    def __init__(self):
        """Initialize notification service"""
        self.settings = get_settings()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
        # Notification statistics
        self.stats = {
            "total_notifications_sent": 0,
            "email_notifications_sent": 0,
            "slack_notifications_sent": 0,
            "discord_notifications_sent": 0,
            "failed_notifications": 0,
            "last_notification_sent": None
        }
        
        logger.info("Notification service initialized")
    
    async def send_trend_alerts(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """
        Send trend alerts to all configured notification channels.
        
        Args:
            alerts: List of trend alerts to send
            
        Returns:
            Dictionary with sending results
        """
        if not alerts:
            return {"alerts_sent": 0, "channels": {}}
        
        logger.info(f"Sending {len(alerts)} trend alerts")
        
        results = {
            "alerts_sent": len(alerts),
            "channels": {},
            "errors": []
        }
        
        # Send to each configured channel
        if self.settings.email_notifications_enabled:
            email_result = await self._send_email_alerts(alerts)
            results["channels"]["email"] = email_result
        
        if self.settings.slack_webhook_url:
            slack_result = await self._send_slack_alerts(alerts)
            results["channels"]["slack"] = slack_result
        
        if self.settings.discord_webhook_url:
            discord_result = await self._send_discord_alerts(alerts)
            results["channels"]["discord"] = discord_result
        
        # Update statistics
        self.stats["total_notifications_sent"] += len(alerts)
        self.stats["last_notification_sent"] = datetime.now()
        
        logger.info(f"Trend alerts sent successfully to {len(results['channels'])} channels")
        return results
    
    async def _send_email_alerts(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """Send alerts via email"""
        try:
            if not all([
                self.settings.smtp_username,
                self.settings.smtp_password,
                self.settings.notification_email
            ]):
                return {"success": False, "error": "Email configuration incomplete"}
            
            # Create email content
            subject = f"🚨 {len(alerts)} New Trend Alert{'s' if len(alerts) > 1 else ''}"
            html_body = self._create_email_html(alerts)
            text_body = self._create_email_text(alerts)
            
            # Create email message
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.smtp_username
            msg["To"] = self.settings.notification_email
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            # Send email
            await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_server,
                port=self.settings.smtp_port,
                start_tls=True,
                username=self.settings.smtp_username,
                password=self.settings.smtp_password
            )
            
            self.stats["email_notifications_sent"] += 1
            logger.info(f"Email alert sent successfully to {self.settings.notification_email}")
            
            return {"success": True, "recipient": self.settings.notification_email}
            
        except Exception as e:
            logger.error(f"Failed to send email alert: {e}")
            self.stats["failed_notifications"] += 1
            return {"success": False, "error": str(e)}
    
    async def _send_slack_alerts(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """Send alerts via Slack webhook"""
        try:
            # Create Slack message
            message = self._create_slack_message(alerts)
            
            # Send to Slack
            response = await self.http_client.post(
                self.settings.slack_webhook_url,
                json=message
            )
            
            if response.status_code == 200:
                self.stats["slack_notifications_sent"] += 1
                logger.info("Slack alert sent successfully")
                return {"success": True, "status_code": response.status_code}
            else:
                error_msg = f"Slack webhook returned status {response.status_code}"
                logger.error(error_msg)
                self.stats["failed_notifications"] += 1
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Failed to send Slack alert: {e}")
            self.stats["failed_notifications"] += 1
            return {"success": False, "error": str(e)}
    
    async def _send_discord_alerts(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """Send alerts via Discord webhook"""
        try:
            # Create Discord message
            message = self._create_discord_message(alerts)
            
            # Send to Discord
            response = await self.http_client.post(
                self.settings.discord_webhook_url,
                json=message
            )
            
            if response.status_code == 204:  # Discord returns 204 for success
                self.stats["discord_notifications_sent"] += 1
                logger.info("Discord alert sent successfully")
                return {"success": True, "status_code": response.status_code}
            else:
                error_msg = f"Discord webhook returned status {response.status_code}"
                logger.error(error_msg)
                self.stats["failed_notifications"] += 1
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Failed to send Discord alert: {e}")
            self.stats["failed_notifications"] += 1
            return {"success": False, "error": str(e)}
    
    def _create_email_html(self, alerts: List[TrendAlert]) -> str:
        """Create HTML email content"""
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .alert {{ border: 1px solid #ddd; margin: 10px 0; padding: 15px; border-radius: 5px; }}
                .viral {{ border-left: 4px solid #ff4444; }}
                .rising {{ border-left: 4px solid #ff8800; }}
                .new_trend {{ border-left: 4px solid #00aa00; }}
                .category_spike {{ border-left: 4px solid #0088cc; }}
                .title {{ font-size: 18px; font-weight: bold; margin-bottom: 10px; }}
                .description {{ color: #666; margin-bottom: 10px; }}
                .stats {{ background: #f5f5f5; padding: 10px; border-radius: 3px; }}
                .confidence {{ float: right; color: #888; }}
                .footer {{ margin-top: 30px; color: #888; font-size: 12px; }}
            </style>
        </head>
        <body>
            <h2>🚨 YouTube Shorts Trend Alerts</h2>
            <p>Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        """
        
        for alert in alerts:
            html += f"""
            <div class="alert {alert.alert_type}">
                <div class="title">{alert.title}</div>
                <div class="confidence">Confidence: {alert.confidence_score:.1%}</div>
                <div class="description">{alert.description}</div>
                <div class="stats">
                    <strong>Channel:</strong> {alert.channel_title}<br>
                    <strong>Category:</strong> {alert.category}<br>
                    <strong>Views:</strong> {alert.current_stats.get('view_count', 0):,}<br>
                    <strong>Engagement:</strong> {alert.current_stats.get('engagement_rate', 0):.2%}<br>
                    <strong>Keywords:</strong> {', '.join(alert.keywords[:5])}<br>
                    <strong>Link:</strong> <a href="{alert.youtube_url}">Watch on YouTube</a>
                </div>
            </div>
            """
        
        html += """
            <div class="footer">
                <p>This alert was generated by the YouTube Shorts Trend Monitoring System.</p>
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _create_email_text(self, alerts: List[TrendAlert]) -> str:
        """Create plain text email content"""
        text = f"""
🚨 YouTube Shorts Trend Alerts
Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

{len(alerts)} new trends detected:

"""
        
        for i, alert in enumerate(alerts, 1):
            text += f"""
Alert {i}: {alert.title}
Type: {alert.alert_type.title()}
Confidence: {alert.confidence_score:.1%}
Channel: {alert.channel_title}
Category: {alert.category}
Views: {alert.current_stats.get('view_count', 0):,}
Engagement: {alert.current_stats.get('engagement_rate', 0):.2%}
Keywords: {', '.join(alert.keywords[:5])}
Link: {alert.youtube_url}

Description: {alert.description}

---
"""
        
        text += """
This alert was generated by the YouTube Shorts Trend Monitoring System.
        """
        
        return text
    
    def _create_slack_message(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """Create Slack message format"""
        emoji_map = {
            "viral": "🚀",
            "rising": "📈",
            "new_trend": "🆕",
            "category_spike": "📊"
        }
        
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"🚨 {len(alerts)} New Trend Alert{'s' if len(alerts) > 1 else ''}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            },
            {
                "type": "divider"
            }
        ]
        
        for alert in alerts[:5]:  # Limit to 5 alerts to avoid message size limits
            emoji = emoji_map.get(alert.alert_type, "🔔")
            
            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{emoji} {alert.title}*\n{alert.description}"
                },
                "accessory": {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "Watch on YouTube"
                    },
                    "url": alert.youtube_url
                }
            })
            
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"*Channel:* {alert.channel_title} | *Category:* {alert.category} | *Confidence:* {alert.confidence_score:.1%}"
                    }
                ]
            })
            
            blocks.append({
                "type": "divider"
            })
        
        if len(alerts) > 5:
            blocks.append({
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"... and {len(alerts) - 5} more alerts"
                    }
                ]
            })
        
        return {"blocks": blocks}
    
    def _create_discord_message(self, alerts: List[TrendAlert]) -> Dict[str, Any]:
        """Create Discord message format"""
        color_map = {
            "viral": 0xFF4444,      # Red
            "rising": 0xFF8800,     # Orange
            "new_trend": 0x00AA00,  # Green
            "category_spike": 0x0088CC  # Blue
        }
        
        embeds = []
        
        # Main embed
        main_embed = {
            "title": f"🚨 {len(alerts)} New Trend Alert{'s' if len(alerts) > 1 else ''}",
            "description": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            "color": 0x5865F2,  # Discord blurple
            "timestamp": datetime.now().isoformat()
        }
        embeds.append(main_embed)
        
        # Alert embeds (limit to 3 to avoid message size limits)
        for alert in alerts[:3]:
            color = color_map.get(alert.alert_type, 0x99AAB5)
            
            embed = {
                "title": alert.title,
                "description": alert.description,
                "color": color,
                "url": alert.youtube_url,
                "thumbnail": {
                    "url": alert.thumbnail_url
                },
                "fields": [
                    {
                        "name": "Channel",
                        "value": alert.channel_title,
                        "inline": True
                    },
                    {
                        "name": "Category",
                        "value": alert.category,
                        "inline": True
                    },
                    {
                        "name": "Confidence",
                        "value": f"{alert.confidence_score:.1%}",
                        "inline": True
                    },
                    {
                        "name": "Views",
                        "value": f"{alert.current_stats.get('view_count', 0):,}",
                        "inline": True
                    },
                    {
                        "name": "Engagement",
                        "value": f"{alert.current_stats.get('engagement_rate', 0):.2%}",
                        "inline": True
                    },
                    {
                        "name": "Keywords",
                        "value": ', '.join(alert.keywords[:3]),
                        "inline": True
                    }
                ]
            }
            embeds.append(embed)
        
        if len(alerts) > 3:
            embeds.append({
                "description": f"... and {len(alerts) - 3} more alerts",
                "color": 0x99AAB5
            })
        
        return {"embeds": embeds}
    
    async def send_weekly_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """
        Send weekly trend report to notification channels.
        
        Args:
            report: Weekly report data
            
        Returns:
            Dictionary with sending results
        """
        logger.info("Sending weekly trend report")
        
        results = {
            "report_sent": True,
            "channels": {},
            "errors": []
        }
        
        # Send to each configured channel
        if self.settings.email_notifications_enabled:
            email_result = await self._send_weekly_email_report(report)
            results["channels"]["email"] = email_result
        
        if self.settings.slack_webhook_url:
            slack_result = await self._send_weekly_slack_report(report)
            results["channels"]["slack"] = slack_result
        
        if self.settings.discord_webhook_url:
            discord_result = await self._send_weekly_discord_report(report)
            results["channels"]["discord"] = discord_result
        
        logger.info(f"Weekly report sent to {len(results['channels'])} channels")
        return results
    
    async def _send_weekly_email_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Send weekly report via email"""
        try:
            subject = f"📊 Weekly YouTube Shorts Trend Report - {report['period']['start'].strftime('%Y-%m-%d')}"
            html_body = self._create_weekly_email_html(report)
            text_body = self._create_weekly_email_text(report)
            
            msg = MIMEMultipart("alternative")
            msg["Subject"] = subject
            msg["From"] = self.settings.smtp_username
            msg["To"] = self.settings.notification_email
            
            msg.attach(MIMEText(text_body, "plain"))
            msg.attach(MIMEText(html_body, "html"))
            
            await aiosmtplib.send(
                msg,
                hostname=self.settings.smtp_server,
                port=self.settings.smtp_port,
                start_tls=True,
                username=self.settings.smtp_username,
                password=self.settings.smtp_password
            )
            
            logger.info("Weekly email report sent successfully")
            return {"success": True, "recipient": self.settings.notification_email}
            
        except Exception as e:
            logger.error(f"Failed to send weekly email report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_weekly_slack_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Send weekly report via Slack"""
        try:
            message = self._create_weekly_slack_message(report)
            
            response = await self.http_client.post(
                self.settings.slack_webhook_url,
                json=message
            )
            
            if response.status_code == 200:
                logger.info("Weekly Slack report sent successfully")
                return {"success": True, "status_code": response.status_code}
            else:
                error_msg = f"Slack webhook returned status {response.status_code}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Failed to send weekly Slack report: {e}")
            return {"success": False, "error": str(e)}
    
    async def _send_weekly_discord_report(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Send weekly report via Discord"""
        try:
            message = self._create_weekly_discord_message(report)
            
            response = await self.http_client.post(
                self.settings.discord_webhook_url,
                json=message
            )
            
            if response.status_code == 204:
                logger.info("Weekly Discord report sent successfully")
                return {"success": True, "status_code": response.status_code}
            else:
                error_msg = f"Discord webhook returned status {response.status_code}"
                logger.error(error_msg)
                return {"success": False, "error": error_msg}
                
        except Exception as e:
            logger.error(f"Failed to send weekly Discord report: {e}")
            return {"success": False, "error": str(e)}
    
    def _create_weekly_email_html(self, report: Dict[str, Any]) -> str:
        """Create HTML weekly report email"""
        start_date = report['period']['start'].strftime('%Y-%m-%d')
        end_date = report['period']['end'].strftime('%Y-%m-%d')
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background: #f0f0f0; padding: 20px; border-radius: 5px; }}
                .summary {{ margin: 20px 0; }}
                .stat {{ display: inline-block; margin: 10px; padding: 10px; border: 1px solid #ddd; border-radius: 3px; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 Weekly YouTube Shorts Trend Report</h2>
                <p><strong>Period:</strong> {start_date} to {end_date}</p>
            </div>
            
            <div class="summary">
                <h3>Summary</h3>
                <div class="stat">
                    <strong>Total Trends:</strong> {report['summary']['total_trends_detected']}
                </div>
                <div class="stat">
                    <strong>Viral Content:</strong> {report['summary']['viral_content_count']}
                </div>
                <div class="stat">
                    <strong>Rising Trends:</strong> {report['summary']['rising_trends_count']}
                </div>
                <div class="stat">
                    <strong>New Trends:</strong> {report['summary']['new_trends_count']}
                </div>
            </div>
            
            <p>This report was generated by the YouTube Shorts Trend Monitoring System.</p>
        </body>
        </html>
        """
        
        return html
    
    def _create_weekly_email_text(self, report: Dict[str, Any]) -> str:
        """Create plain text weekly report email"""
        start_date = report['period']['start'].strftime('%Y-%m-%d')
        end_date = report['period']['end'].strftime('%Y-%m-%d')
        
        text = f"""
📊 Weekly YouTube Shorts Trend Report
Period: {start_date} to {end_date}

Summary:
- Total Trends Detected: {report['summary']['total_trends_detected']}
- Viral Content: {report['summary']['viral_content_count']}
- Rising Trends: {report['summary']['rising_trends_count']}
- New Trends: {report['summary']['new_trends_count']}
- Category Spikes: {report['summary']['category_spikes_count']}

This report was generated by the YouTube Shorts Trend Monitoring System.
        """
        
        return text
    
    def _create_weekly_slack_message(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Create Slack weekly report message"""
        start_date = report['period']['start'].strftime('%Y-%m-%d')
        end_date = report['period']['end'].strftime('%Y-%m-%d')
        
        return {
            "blocks": [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "📊 Weekly YouTube Shorts Trend Report"
                    }
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": f"Period: {start_date} to {end_date}"
                        }
                    ]
                },
                {
                    "type": "section",
                    "fields": [
                        {
                            "type": "mrkdwn",
                            "text": f"*Total Trends:* {report['summary']['total_trends_detected']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Viral Content:* {report['summary']['viral_content_count']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*Rising Trends:* {report['summary']['rising_trends_count']}"
                        },
                        {
                            "type": "mrkdwn",
                            "text": f"*New Trends:* {report['summary']['new_trends_count']}"
                        }
                    ]
                }
            ]
        }
    
    def _create_weekly_discord_message(self, report: Dict[str, Any]) -> Dict[str, Any]:
        """Create Discord weekly report message"""
        start_date = report['period']['start'].strftime('%Y-%m-%d')
        end_date = report['period']['end'].strftime('%Y-%m-%d')
        
        return {
            "embeds": [
                {
                    "title": "📊 Weekly YouTube Shorts Trend Report",
                    "description": f"Period: {start_date} to {end_date}",
                    "color": 0x5865F2,
                    "fields": [
                        {
                            "name": "Total Trends",
                            "value": str(report['summary']['total_trends_detected']),
                            "inline": True
                        },
                        {
                            "name": "Viral Content",
                            "value": str(report['summary']['viral_content_count']),
                            "inline": True
                        },
                        {
                            "name": "Rising Trends",
                            "value": str(report['summary']['rising_trends_count']),
                            "inline": True
                        },
                        {
                            "name": "New Trends",
                            "value": str(report['summary']['new_trends_count']),
                            "inline": True
                        }
                    ],
                    "timestamp": datetime.now().isoformat()
                }
            ]
        }
    
    async def test_notifications(self) -> Dict[str, Any]:
        """Test all notification channels"""
        test_alert = TrendAlert(
            alert_id="test_alert_123",
            alert_type="viral",
            title="🧪 Test Alert - Notification System Working",
            description="This is a test alert to verify notification channels are working correctly.",
            video_id="test_video_123",
            channel_title="Test Channel",
            current_stats={"view_count": 100000, "engagement_rate": 0.05},
            growth_metrics={"days_since_published": 1},
            confidence_score=0.95,
            detected_at=datetime.now(),
            category="Challenge",
            keywords=["test", "notification", "system"],
            youtube_url="https://youtube.com/watch?v=test_video_123",
            thumbnail_url="https://i.ytimg.com/vi/test_video_123/maxresdefault.jpg"
        )
        
        return await self.send_trend_alerts([test_alert])
    
    async def get_notification_stats(self) -> Dict[str, Any]:
        """Get notification statistics"""
        return self.stats
    
    async def close(self):
        """Close the notification service"""
        await self.http_client.aclose()
        logger.info("Notification service closed")


# Global notification service instance
_notification_service = None


def get_notification_service() -> NotificationService:
    """Get the global notification service instance"""
    global _notification_service
    if _notification_service is None:
        _notification_service = NotificationService()
    return _notification_service