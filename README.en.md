# ZeroTier Monitor

A script for active monitoring of node (computer) status in one or more ZeroTier networks. It tracks online status, client version currency, and sends notifications about issues to Telegram.

## Key Features

- **Multi-network Monitoring**: Supports multiple ZeroTier networks with different access tokens.
- **Status Tracking**: Checks if a node is online and how long it has been active.
- **Client Version Check**: Compares the ZeroTier client version on a node with the latest official version on GitHub.
- **Smart Notifications**: Sends messages to Telegram only when a problem is detected or when service is restored.
- **Alert Escalation**: Different notification levels depending on the duration of the offline state (e.g., after 5 minutes, 15 minutes, 1 hour).
- **Ping Check**: When a node is detected as offline, it performs an additional check of its availability via IP address using ICMP (ping).
- **Daily Reports**: Every day at midnight, it sends a summary report on the number of checks and incidents detected over the past day.
- **Local Database**: Uses SQLite to store node states between checks, which helps to avoid false positives.
- **API Failure Resilience**: Implemented retries for network requests to the ZeroTier and Telegram APIs.
- **Anomaly Detection**: Smooths out rare anomalous spikes in `lastSeen` data from the ZeroTier API.

## How It Works

1.  **Initialization**: On startup, the script reads the configuration from the `.env` file, initializes the SQLite database, and sends a startup notification.
2.  **Infinite Loop**: The script runs in an infinite loop with a specified interval (`CHECK_INTERVAL_SECONDS`).
3.  **Data Fetching**: In each cycle, it requests the list of all members of the specified networks from the ZeroTier API and the latest client version from GitHub.
4.  **Node Analysis**: For each monitored node (`MEMBER_IDS`), the script:
    - Compares its state with the one saved in the local database.
    - Checks the last activity time (`lastSeen`). If the node has been inactive for a long time, a report is generated.
    - Checks the client version. If the version is outdated, a report is generated.
    - If an offline report is generated, an additional ping check is performed.
5.  **Sending Reports**: If problem reports have been generated, they are combined into a single message and sent to Telegram.
6.  **State Saving**: The new state of each node (online status, sent notifications) is saved to the database.
7.  **Daily Summary**: Once a day, the script sends a summary report for the past day and resets the daily counters.

## Installation and Setup

### 1. Clone the repository

```bash
git clone https://github.com/sarvensky/zero_monitor.git
cd zero_monitor
```

### 2. Install dependencies

Make sure you have Python 3.6+ and pip installed.

```bash
pip install -r requirements.txt
```

### 3. Configure the application

Create a `.env` file in the project's root folder by copying the contents from `.env.example`, and fill it with your data.

```bash
cp .env.example .env
```

Open the `.env` file in a text editor and specify the values for the following variables:

- `ZEROTIER_NETWORKS_JSON`: A JSON string with your network data.
- `MEMBER_IDS_CSV`: The IDs of the nodes to monitor, separated by commas.
- `TELEGRAM_BOT_TOKEN`: The token for your Telegram bot.
- `TELEGRAM_CHAT_ID`: The ID of the chat or channel in Telegram for sending notifications.
- `CHECK_INTERVAL_SECONDS` (optional): The check interval in seconds (default is 300).

## Running the script

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
  - The token received from @BotFather when creating a bot.

- **`TELEGRAM_CHAT_ID`**:
  - The unique identifier of the chat where the bot will send messages. You can find it out using the @userinfobot.

- **`CHECK_INTERVAL_SECONDS`**:
  - **Format**: Integer.
  - **Description**: How often (in seconds) the script will perform a check.
  - **Default**: `300` (5 minutes).