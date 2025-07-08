# ZeroTier Monitor

[Русская версия](README.md)

A script for active monitoring of node (computer) status in one or more ZeroTier networks. It tracks online status, client version currency, and sends notifications about issues to Telegram.

## Key Features

- **Multi-Network Monitoring**: Supports multiple ZeroTier networks with different access tokens.
- **Status Tracking**: Checks if a node is online and how long it has been active.
- **Client Version Check**: Compares the ZeroTier client version on a node with the latest official version from GitHub.
- **Smart Notifications**: Sends messages to Telegram only when a problem is detected or resolved.
- **Alert Escalation**: Different notification levels depending on the offline duration (e.g., after 5 minutes, 15 minutes, 1 hour).
- **Ping Check**: When a node is detected as offline, it performs an additional ICMP (ping) check to verify its IP address accessibility.
- **Daily Reports**: Sends a summary report every day at midnight with the number of checks and incidents detected over the past day.
- **Local Database**: Uses SQLite to store node states between checks, preventing false positives.
- **API Failure Resilience**: Implemented retry logic for network requests to the ZeroTier and Telegram APIs.
- **Anomaly Detection**: Smooths out rare, anomalous spikes in `lastSeen` data from the ZeroTier API.

## How It Works

1.  **Initialization**: On startup, the script reads the configuration from the `.env` file, initializes the SQLite database, and sends a startup notification.
2.  **Infinite Loop**: The script runs in an infinite loop with a configurable interval (`CHECK_INTERVAL_SECONDS`).
3.  **Data Fetching**: In each cycle, it queries the ZeroTier API for a list of all members in the specified networks and the latest client version from GitHub.
4.  **Node Analysis**: For each monitored node (`MEMBER_IDS`), the script:
    - Compares its current state with the one saved in the local database.
    - Checks the last activity time (`lastSeen`). If the node has been inactive for too long, a report is generated.
    - Checks the client version. If the version is outdated, a report is generated.
    - If an offline report is generated, an additional ping check is performed.
5.  **Sending Reports**: If any problem reports were generated, they are combined into a single message and sent to Telegram.
6.  **State Saving**: The new state of each node (online status, sent notifications) is saved to the database.
7.  **Daily Summary**: Once a day, the script sends a summary report for the past day and resets the daily counters.

## Installation and Setup

### 1. Clone the Repository

```bash
git clone https://github.com/sarvensky/zero_monitor.git
cd zero_monitor
```

### 2. Install Dependencies

Make sure you have Python 3.6+ and pip installed.

```bash
pip install -r requirements.txt
```

### 3. Configure the Environment

Create a `.env` file in the project's root directory by copying the contents from `.env.example`, and fill it with your data.

```bash
cp .env.example .env
```

Open the `.env` file in a text editor and set the values for the following variables:

- `ZEROTIER_NETWORKS_JSON`: A JSON string with your network data.
- `MEMBER_IDS_CSV`: Comma-separated list of node IDs to monitor.
- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token.
- `TELEGRAM_CHAT_ID`: The ID of the Telegram chat or channel for sending notifications.
- `CHECK_INTERVAL_SECONDS` (optional): The check interval in seconds (default is 300).
- `LANGUAGE` (optional): The language for logs and notifications. `RU` or `EN` (default is `RU`).

## Running the Script

To start monitoring, use `START.bat` (for Windows) or `start.sh` (for Linux), or run the command directly:

```bash
python main.py
```

The script will start running in the console, displaying logs and sending notifications to Telegram as needed.

## Detailed Configuration (`.env`)

- **`ZEROTIER_NETWORKS_JSON`**:
  - **Format**: JSON array (list) of objects.
  - **Each object must contain**:
    - `token`: API token for accessing the ZeroTier network.
    - `network_id`: Your ZeroTier network ID.
  - **Example for one network**:
    ```json
    [{"token": "YOUR_ZEROTIER_API_TOKEN", "network_id": "YOUR_NETWORK_ID"}]
    ```
  - **Example for two networks**:
    ```json
    [
      {"token": "TOKEN_1", "network_id": "NETWORK_ID_1"},
      {"token": "TOKEN_2", "network_id": "NETWORK_ID_2"}
    ]
    ```

- **`MEMBER_IDS_CSV`**:
  - **Format**: A string containing 10-digit ZeroTier node IDs, separated by commas.
  - **Example**:
    ```
    1234567890,0987654321,abcdef1234
    ```

- **`TELEGRAM_BOT_TOKEN`**:
  - The token obtained from @BotFather when creating a bot.

- **`TELEGRAM_CHAT_ID`**:
  - The unique identifier for the chat where the bot will send messages. You can find it using a bot like @userinfobot.

- **`CHECK_INTERVAL_SECONDS`**:
  - **Format**: Integer.
  - **Description**: How often (in seconds) the script will perform a check.
  - **Default**: `300` (5 minutes).

- **`LANGUAGE`**:
  - **Format**: `RU` or `EN`.
  - **Description**: Sets the language for console logs and Telegram notifications.
  - **Default**: `RU`.