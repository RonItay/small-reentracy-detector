# Tiny Reentrancy detector

## How is reentrancy detected

### Light reentrancy

If contract A calls contract B, and in this same call B calls A.

This detection method. leads to alot of false positives, since it is very general.

### Hard reentrancy
Assume function a1 in contract A.
if A.a1 call contract B, and in this same call A.a1 is called again.

## How to recognize a smart contract transaction.

I recognize if a transaction is a smart contract invocation by seeing data being passed to the destination.
This can lead to false positives, but this is done to save the API calls required to check each address in the block.

## running
Install requirements using:
```pip3 install -r requirements.txt```

run by running main.py
```python3 main.py```

And environment variable with nad API_KEY to dRPC is required. This is a legacy requirement and can be changed.
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