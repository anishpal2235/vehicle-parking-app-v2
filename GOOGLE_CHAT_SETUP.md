# Google Chat Notifications Setup Guide

This guide will help you set up Google Chat notifications for the Parking Management System.

## Prerequisites

- A Google Workspace account (or personal Google account)
- Access to Google Chat
- Ability to create webhooks

## Step 1: Create a Google Chat Webhook

### Option A: Using Google Chat Webhook (Recommended)

1. **Open Google Chat** in your browser
2. **Create a new space** or use an existing space
3. **Add a webhook**:
   - Click on the space name at the top
   - Select "Manage webhooks"
   - Click "Add webhook"
   - Give it a name (e.g., "Parking App Notifications")
   - Click "Save"
4. **Copy the webhook URL** - it will look like:
   ```
   https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN
   ```

### Option B: Using Google Apps Script (Alternative)

1. **Go to [Google Apps Script](https://script.google.com/)**
2. **Create a new project**
3. **Add this code**:

```javascript
function doPost(e) {
  var data = JSON.parse(e.postData.contents);
  var spaceId = "YOUR_SPACE_ID"; // Replace with your space ID
  
  var message = {
    "text": data.text,
    "cards": data.cards
  };
  
  var options = {
    "method": "post",
    "headers": {
      "Content-Type": "application/json"
    },
    "payload": JSON.stringify(message)
  };
  
  var webhookUrl = "https://chat.googleapis.com/v1/spaces/" + spaceId + "/messages?key=YOUR_KEY&token=YOUR_TOKEN";
  UrlFetchApp.fetch(webhookUrl, options);
  
  return ContentService.createTextOutput("OK");
}
```

4. **Deploy as web app** and copy the URL

## Step 2: Configure the Application

### Environment Variable Method (Recommended)

Set the webhook URL as an environment variable:

```bash
# Windows (PowerShell)
$env:GCHAT_WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN"

# Windows (Command Prompt)
set GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN

# Linux/Mac
export GCHAT_WEBHOOK_URL="https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN"
```

### Configuration File Method

Add to your `.env` file:

```env
GCHAT_WEBHOOK_URL=https://chat.googleapis.com/v1/spaces/SPACE_ID/messages?key=KEY&token=TOKEN
```

## Step 3: Test the Configuration

Run the test script to verify Google Chat notifications work:

```bash
python test_gchat_notifications.py
```

## Step 4: Configure User Preferences

1. **Log into the Parking App**
2. **Go to User Preferences**
3. **Select "Google Chat Notifications"**
4. **Enter your Google Chat email address**
5. **Save preferences**

## Features Available

### Daily Reminders
- Receive daily parking reminders via Google Chat
- Includes personalized message with user's name
- Shows reminder time and report format preferences

### Monthly Report Downloads
- Direct download buttons for monthly reports
- Respects user's preferred format (HTML/PDF)
- Links to dashboard for easy access

### Rich Notifications
- **Card-based layout** with header information
- **Interactive buttons** for dashboard and report downloads
- **User preferences display** (reminder time, report format)
- **Emoji icons** for better visual appeal

## Notification Types

### 1. Daily Reminders
- **Trigger**: Scheduled daily at user's preferred time
- **Content**: Personalized reminder message
- **Actions**: Dashboard link, Monthly report download

### 2. Monthly Reports
- **Trigger**: 1st of each month at 1:00 AM
- **Content**: Monthly activity summary
- **Actions**: Report download in preferred format

### 3. CSV Export Notifications
- **Trigger**: When user requests data export
- **Content**: Export completion notification
- **Actions**: Direct download link

## Troubleshooting

### Common Issues

1. **"Webhook not configured" error**
   - Ensure `GCHAT_WEBHOOK_URL` environment variable is set
   - Check webhook URL format and validity

2. **"Failed to send Google Chat notification" error**
   - Verify webhook URL is correct
   - Check if webhook is still active in Google Chat
   - Ensure proper permissions

3. **Notifications not appearing in Google Chat**
   - Check if the webhook is added to the correct space
   - Verify the space is active and accessible
   - Test webhook manually using curl or Postman

### Testing Webhook Manually

```bash
curl -X POST -H "Content-Type: application/json" \
  -d '{"text":"Test message from Parking App"}' \
  "YOUR_WEBHOOK_URL"
```

### Security Considerations

- **Keep webhook URLs private** - don't commit them to version control
- **Use environment variables** for configuration
- **Regularly rotate webhook tokens** if possible
- **Monitor webhook usage** for unusual activity

## Support

If you encounter issues:

1. Check the application logs for error messages
2. Verify webhook configuration
3. Test webhook manually
4. Check Google Chat space settings
5. Ensure user preferences are correctly set

## Example Notification

```
🚗 Parking Reminder
Generated on Saturday, August 23, 2025 at 11:00 PM

Hello John Doe, don't forget to book your parking spot for tomorrow if needed!

📊 Monthly Report Format: PDF
⏰ Reminder Time: 23:00

[📱 GO TO DASHBOARD] [📥 DOWNLOAD PDF REPORT]
```
