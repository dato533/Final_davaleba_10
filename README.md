# ConnectHub

A modern social networking web application built with **Django**, **Django Channels**, and **WebSockets**. ConnectHub allows users to create posts, communicate in real time, and share media with friends.

---

## Features

### Authentication
- User Registration
- User Login & Logout
- Email Authentication
- Password Change
- Password Reset
- User Profile Management

---

## Profile

- Edit Profile Information
- Upload Profile Picture
- Upload Cover Image
- View Other User Profiles

---

## Posts

- Create Posts
- Edit Posts
- Delete Posts
- Like / Unlike Posts
- Comment on Posts
- Edit Comments
- Delete Comments
- Multiple Image Upload
- Video Upload
- File Upload

---

## Real-Time Chat

Powered by **Django Channels** and **WebSockets**

### Private Chats

- Real-Time Messaging
- Typing Indicator
- Read Receipts (✓ / ✓✓)
- Image Messages
- Video Messages
- File Sharing

### Group Chats

- Create Group Conversations
- Real-Time Group Messaging
- Media Sharing
- Notifications

---

## Notifications

- Friend Request Notifications
- Message Notifications
- Like Notifications
- Comment Notifications

---

## Media Support

Users can share:

- Images
- Videos
- Documents
- Other Files

---

## Technologies

- Python 3.9
- Django 4.2
- Django Channels
- Daphne
- SQLite3
- HTML5
- CSS3
- JavaScript
- WebSockets

---

## Installation

Clone the repository

```bash
git clone https://github.com/dato533/ConnectHub.git
```

Go to the project directory

```bash
cd ConnectHub
```

Create a virtual environment

```bash
python -m venv env
```

Activate the virtual environment

### Windows

```bash
env\Scripts\activate
```

### Linux / macOS

```bash
source env/bin/activate
```

Install dependencies

```bash
pip install -r requirements.txt
```

Apply migrations

```bash
python manage.py migrate
```

Create a superuser

```bash
python manage.py createsuperuser
```

Run the development server

```bash
python manage.py runserver
```

Open your browser

```
http://127.0.0.1:8000/
```

---

## Project Structure

```
ConnectHub/
│
├── chat/
├── notifications/
├── posts/
├── users/
├── social/
├── media/
├── static/
├── templates/
├── manage.py
└── requirements.txt
```

---

## Screenshots

### Home Feed
- Create posts
- Like posts
- Comment on posts

### Chat
- Real-time messaging
- Image sharing
- Video sharing
- File sharing
- Read receipts
- Typing indicator

### Profile
- Edit profile
- Upload avatar
- Upload cover photo

---

## Future Improvements

- Voice Messages
- Video Calls
- Message Search
- Emoji Reactions
- Story System
- Dark Mode
- Push Notifications

---

## Author

**Dato Nikolaishvili**

GitHub:
https://github.com/dato533

---

## License

This project was created for educational purposes.