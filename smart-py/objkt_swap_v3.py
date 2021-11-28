"""Prototype for the next version of the H=N marketplace contract.

This version corrects several small bugs from the v2 marketplace contract and
adds the possibility to trade different kinds of FA2 tokens.

"""

import smartpy as sp


class Marketplace(sp.Contract):
    """This contract implements the next version of the H=N marketplace
    contract.

    """

    def __init__(self, manager, metadata, objkt, fee):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            manager=sp.TAddress,
            fee_recipient=sp.TAddress,
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            allowed_fa2s=sp.TSet(sp.TAddress),
            swaps=sp.TBigMap(sp.TNat, sp.TRecord(
                issuer=sp.TAddress,
                fa2=sp.TAddress,
                objkt_id=sp.TNat,
                objkt_amount=sp.TNat,
                xtz_per_objkt=sp.TMutez,
                royalties=sp.TNat,
                creator=sp.TAddress)),
            fee=sp.TNat,
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            manager=manager,
            fee_recipient=manager,
            metadata=metadata,
            allowed_fa2s=sp.set([objkt]),
            swaps=sp.big_map(),
            fee=fee,
            counter=0)

    def check_is_manager(self):
        """Checks that the address that called the entry point is the contract
        manager.

        """
        sp.verify(sp.sender == self.data.manager,
                  message="This can only be executed by the contract manager.")

    @sp.entry_point
    def swap(self, params):
        """Swaps several editions of a token for a fixed price.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            fa2=sp.TAddress,
            objkt_id=sp.TNat,
            objkt_amount=sp.TNat,
            xtz_per_objkt=sp.TMutez,
            royalties=sp.TNat,
            creator=sp.TAddress))

        # Check that the token is one of the allowed tokens to trade
        sp.verify(self.data.allowed_fa2s.contains(params.fa2),
                  message="This token type cannot be traded in the marketplace.")

        # Check that at least one edition will be swapped
        sp.verify(params.objkt_amount > 0,
                  message="You need to swap at least one token edition.")

        # Check that the royalties are within the expected limits
        sp.verify(params.royalties <= 250,
                  message="The royalties cannot be higher than 25%.")

        # Transfer all the editions to the marketplace account
        self.fa2_transfer(
            fa2=params.fa2,
            from_=sp.sender,
            to_=sp.self_address,
            objkt_id=params.objkt_id,
            objkt_amount=params.objkt_amount)

        # Update the swaps bigmap with the new swap information
        self.data.swaps[self.data.counter] = sp.record(
            issuer=sp.sender,
            fa2=params.fa2,
            objkt_id=params.objkt_id,
            objkt_amount=params.objkt_amount,
            xtz_per_objkt=params.xtz_per_objkt,
            royalties=params.royalties,
            creator=params.creator)

        # Increase the swaps counter
        self.data.counter += 1

    @sp.entry_point
    def collect(self, params):
        """Collects one edition of a token that has already been swapped.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(params),
                  message="The provided swap_id doesn't exist.")

        # Check that the provided tez amount is exactly the edition price
        sp.verify(
            sp.amount == self.data.swaps[params].xtz_per_objkt,
            message="The sent tez amount does not coincide with the edition price.")

        # Check that there is at least one edition available to collect
        sp.verify(
            self.data.swaps[params].objkt_amount > 0,
            message="All editions for this swap have already been collected.")

        # Handle tez tranfers if the edition price is not zero
        sp.if self.data.swaps[params].xtz_per_objkt != sp.tez(0):
            # Send the royalties to the NFT creator
            self.royalties_amount = sp.split_tokens(
                self.data.swaps[params].xtz_per_objkt,
                self.data.swaps[params].royalties, 1000)

            sp.if self.royalties_amount > sp.mutez(0):
                sp.send(self.data.swaps[params].creator, self.royalties_amount)

            # Send the management fees
            self.fee_amount = sp.split_tokens(
                self.data.swaps[params].xtz_per_objkt, self.data.fee, 1000)

            sp.if self.fee_amount > sp.mutez(0):
                sp.send(self.data.fee_recipient, self.fee_amount)

            # Send what is left to the swap issuer
            sp.send(self.data.swaps[params].issuer,
                    sp.amount - self.royalties_amount - self.fee_amount)

        # Transfer the token edition to the collector
        self.fa2_transfer(
            fa2=self.data.swaps[params].fa2,
            from_=sp.self_address,
            to_=sp.sender,
            objkt_id=self.data.swaps[params].objkt_id,
            objkt_amount=1)

        # Update the number of editions available in the swaps big map
        self.data.swaps[params].objkt_amount = sp.as_nat(
            self.data.swaps[params].objkt_amount - 1)

    @sp.entry_point
    def cancel_swap(self, params):
        """Cancels an existing swap.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(params),
                  message="The provided swap_id doesn't exist.")

        # Check that the swap issuer is cancelling the swap
        sp.verify(sp.sender == self.data.swaps[params].issuer,
                  message="Only the swap issuer can cancel the swap.")

        # Check that there is at least one swapped edition
        sp.verify(self.data.swaps[params].objkt_amount > 0,
                  message="All editions have been collected.")

        # Transfer the remaining token editions back to the owner
        self.fa2_transfer(
            fa2=self.data.swaps[params].fa2,
            from_=sp.self_address,
            to_=sp.sender,
            objkt_id=self.data.swaps[params].objkt_id,
            objkt_amount=self.data.swaps[params].objkt_amount)

        # Delete the swap entry in the the swaps big map
        del self.data.swaps[params]

    @sp.entry_point
    def update_fee(self, params):
        """Updates the marketplace management fees.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TNat)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that the new fee is not larger than 25%
        sp.verify(params <= 250,
                  message="The management fee cannot be higher than 25%.")

        # Set the new management fee
        self.data.fee = params

    @sp.entry_point
    def update_fee_recipient(self, params):
        """Updates the marketplace management fee recipient address.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Set the new management fee recipient address
        self.data.fee_recipient = params

    @sp.entry_point
    def update_manager(self, params):
        """Updates the marketplace manager address.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Set the new manager address
        self.data.manager = params

    @sp.entry_point
    def add_fa2_address(self, params):
        """Adds a new FA2 token address to the list of tradable tokens.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Add the new FA2 token address
        self.data.allowed_fa2s.add(params)

    @sp.entry_point
    def remove_fa2_address(self, params):
        """Removes one of the tradable FA2 token address.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that the FA2 token address is present in the set
        sp.verify(self.data.allowed_fa2s.contains(params),
                  message="The FA2 token is not present in the list of tradable tokens.")

        # Remove the new FA2 token address from the set
        self.data.allowed_fa2s.remove(params)

    def fa2_transfer(self, fa2, from_, to_, objkt_id, objkt_amount):
        """Transfers a number of editions of a FA2 token between to addresses.

        """
        # Get a handle to the FA2 token transfer entry point
        c = sp.contract(
            t=sp.TList(sp.TRecord(
                from_=sp.TAddress,
                txs=sp.TList(sp.TRecord(
                    to_=sp.TAddress,
                    token_id=sp.TNat,
                    amount=sp.TNat).layout(("to_", ("token_id", "amount")))))),
            address=fa2,
            entry_point="transfer").open_some()

        # Transfer the FA2 token editions to the new address
        sp.transfer(
            arg=sp.list([sp.record(
                from_=from_,
                txs=sp.list([sp.record(
                    to_=to_,
                    token_id=objkt_id,
                    amount=objkt_amount)]))]),
            amount=sp.mutez(0),
            destination=c)
