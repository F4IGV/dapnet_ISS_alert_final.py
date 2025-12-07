ISS Alert Script for DAPNET (By F4IGV and ChatGPT)

This project provides a complete Python script to detect upcoming ISS passes and send real time alerts through the DAPNET pager network.
All calculations are done in UTC using Skyfield, and messages are formatted in ASCII only to ensure full compatibility with POCSAG pagers.

Main Features

Automatic download of ISS TLE data from AMSAT and Celestrak

Pass prediction for the next 2 hours using Skyfield

Detection of 4 key events:

Prealert (15 min before rise)

Start of visibility

Maximum elevation

End of pass

Real time azimuth and elevation computation for each alert

Automatic DAPNET message sending

State stored in a JSON file to prevent duplicate messages

Automatic reset after each completed pass

Detailed local and UTC logging for debugging

Fully ASCII (no accented characters) for pager compatibility

Message Format

Prealert: azimuth only

Start, Peak, End: azimuth and elevation
Messages include local time (HH:MM).

Configuration

You can customize:

DAPNET user, password, callsigns and transmitter groups

Observer location (lat, lon, altitude)

Minimum elevation, time windows and pass expiration

Requirements

Python 3.x

Packages:

requests

skyfield

Install dependencies:

pip install requests skyfield

How It Works

The script:

Loads or initializes pass state

Downloads fresh TLE data

Computes upcoming ISS pass

Checks timing windows every run

Sends alerts through DAPNET when conditions match

Logs all operations

Resets once the pass is over

It is designed to be triggered every minute using cron or Windows Task Scheduler.

Purpose

This tool is intended for ham radio operators who want ISS pass alerts directly on their POCSAG pagers through the DAPNET network.
It is reliable, fully autonomous, and simple to integrate into a home server or Raspberry Pi.
