@wip
Feature: Withdraw cash
  Account holders can withdraw cash when funds are sufficient
  and the daily limit has not been reached.

  Rule: A withdrawal cannot exceed the available balance

    Example: Withdrawal within balance succeeds
      Given Alice has a balance of NT$1000
      When Alice withdraws NT$300
      Then Alice should receive NT$300
      And Alice's balance should be NT$700

    Example: Withdrawal over balance is rejected
      Given Bob has a balance of NT$100
      When Bob withdraws NT$500
      Then Bob should be told "Insufficient funds"
      And Bob's balance should be NT$100

  Rule: The daily withdrawal limit is NT$20000

    Example: Withdrawal up to the daily limit is approved
      Given Carol has a balance of NT$50000
      And Carol has already withdrawn NT$15000 today
      When Carol withdraws NT$5000
      Then the withdrawal should be approved

    Example: Withdrawal over the daily limit is rejected
      Given Carol has a balance of NT$50000
      And Carol has already withdrawn NT$15000 today
      When Carol withdraws NT$5001
      Then the withdrawal should be rejected
