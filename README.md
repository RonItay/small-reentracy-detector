# Tiny Reentrancy detector

## How is reentrancy defined

### Light reentrancy

If contract A calls contract B, and in this same call B calls A.

This definition leads to alot of false positives for sure.

### Hard

If function 1 in contract A calls contract B, and in this same call function 1 of contract A is called.

## How to recognize a smart contract transaction.

I recognize by seeing data being passed to the destination.
This can lead to false positives, but this is done to save API calls to check each destination in the block.

## running

Running main.py file.
Prints suspicious transaction's hash and their suspicion level.

## Components

### block notifier

listens to the network and calls a callback when a new block is created.
Two are implemented:

- Pull: constantly checks the network for new blocks.
- Push: Subscribes to a websocket for push notifications. This is currently broken, and not used, since the "free"
  subscription is currently broken as well.

### block analyzer

Carries the most logic.

Recursively iterates over calls to find reentrancy conditions.

Recursion is bad, but it was the easiest to implement quickly, a queue would do better of course.