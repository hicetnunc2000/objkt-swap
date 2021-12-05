"""Prototype for the next version of the H=N marketplace contract.

This version corrects several small bugs from the v2 marketplace contract and
adds the possibility to trade different kinds of FA2 tokens.

"""

import smartpy as sp


class Marketplace(sp.Contract):
    """This contract implements the next version of the H=N marketplace
    contract.

    """

    SWAP_TYPE = sp.TRecord(
        # The user that created the swap
        issuer=sp.TAddress,
        # The token FA2 contract address
        fa2=sp.TAddress,
        # The token id (not necessarily from a OBJKT)
        objkt_id=sp.TNat,
        # The number of swapped editions
        objkt_amount=sp.TNat,
        # The price of each edition in mutez
        xtz_per_objkt=sp.TMutez,
        # The artists royalties in (1000 is 100%)
        royalties=sp.TNat,
        # The address that will receive the royalties
        creator=sp.TAddress).layout(
            ("issuer", ("fa2", ("objkt_id", ("objkt_amount", ("xtz_per_objkt", ("royalties", "creator")))))))

    def __init__(self, manager, metadata, allowed_fa2s, fee):
        """Initializes the contract.

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            manager=sp.TAddress,
            fee_recipient=sp.TAddress,
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            allowed_fa2s=sp.TBigMap(sp.TAddress, sp.TBool),
            swaps=sp.TBigMap(sp.TNat, Marketplace.SWAP_TYPE),
            fee=sp.TNat,
            counter=sp.TNat))

        # Initialize the contract storage
        self.init(
            manager=manager,
            fee_recipient=manager,
            metadata=metadata,
            allowed_fa2s=allowed_fa2s,
            swaps=sp.big_map(),
            fee=fee,
            counter=0)

    def check_is_manager(self):
        """Checks that the address that called the entry point is the contract
        manager.

        """
        sp.verify(sp.sender == self.data.manager,
                  message="This can only be executed by the manager")

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
        sp.verify(self.data.allowed_fa2s.get(params.fa2, default_value=False),
                  message="This token type cannot be traded")

        # Check that at least one edition will be swapped
        sp.verify(params.objkt_amount > 0,
                  message="At least one edition needs to be swapped")

        # Check that the royalties are within the expected limits
        sp.verify(params.royalties <= 250,
                  message="The royalties cannot be higher than 25%")

        # Transfer all the editions to the marketplace account
        self.fa2_transfer(
            fa2=params.fa2,
            from_=sp.sender,
            to_=sp.self_address,
            token_id=params.objkt_id,
            token_amount=params.objkt_amount)

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
    def collect(self, swap_id):
        """Collects one edition of a token that has already been swapped.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id),
                  message="The provided swap_id doesn't exist")

        # Check that the provided tez amount is exactly the edition price
        swap = self.data.swaps[swap_id]
        sp.verify(sp.amount == swap.xtz_per_objkt,
                  message="The sent tez amount does not coincide with the edition price")

        # Check that there is at least one edition available to collect
        sp.verify(swap.objkt_amount > 0,
                  message="All editions have already been collected")

        # Handle tez tranfers if the edition price is not zero
        sp.if swap.xtz_per_objkt != sp.tez(0):
            # Send the royalties to the NFT creator
            royalties_amount = sp.local(
                "royalties_amount", sp.split_tokens(swap.xtz_per_objkt, swap.royalties, 1000))

            sp.if royalties_amount.value > sp.mutez(0):
                sp.send(swap.creator, royalties_amount.value)

            # Send the management fees
            fee_amount = sp.local(
                "fee_amount", sp.split_tokens(swap.xtz_per_objkt, self.data.fee, 1000))

            sp.if fee_amount.value > sp.mutez(0):
                sp.send(self.data.fee_recipient, fee_amount.value)

            # Send what is left to the swap issuer
            sp.send(swap.issuer, sp.amount - royalties_amount.value - fee_amount.value)

        # Transfer the token edition to the collector
        self.fa2_transfer(
            fa2=swap.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=swap.objkt_id,
            token_amount=1)

        # Update the number of editions available in the swaps big map
        swap.objkt_amount = sp.as_nat(swap.objkt_amount - 1)

    @sp.entry_point
    def cancel_swap(self, swap_id):
        """Cancels an existing swap.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id),
                  message="The provided swap_id doesn't exist")

        # Check that the swap issuer is cancelling the swap
        swap = self.data.swaps[swap_id]
        sp.verify(sp.sender == swap.issuer,
                  message="Only the swap issuer can cancel the swap")

        # Check that there is at least one swapped edition
        sp.verify(swap.objkt_amount > 0,
                  message="All editions have been collected")

        # Transfer the remaining token editions back to the owner
        self.fa2_transfer(
            fa2=swap.fa2,
            from_=sp.self_address,
            to_=sp.sender,
            token_id=swap.objkt_id,
            token_amount=swap.objkt_amount)

        # Delete the swap entry in the the swaps big map
        del self.data.swaps[swap_id]

    @sp.entry_point
    def update_fee(self, new_fee):
        """Updates the marketplace management fees.

        """
        # Define the input parameter data type
        sp.set_type(new_fee, sp.TNat)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= 250,
                  message="The management fee cannot be higher than 25%")

        # Set the new management fee
        self.data.fee = new_fee

    @sp.entry_point
    def update_fee_recipient(self, new_fee_recipient):
        """Updates the marketplace management fee recipient address.

        """
        # Define the input parameter data type
        sp.set_type(new_fee_recipient, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Set the new management fee recipient address
        self.data.fee_recipient = new_fee_recipient

    @sp.entry_point
    def update_manager(self, new_manager):
        """Updates the marketplace manager address.

        """
        # Define the input parameter data type
        sp.set_type(new_manager, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Set the new manager address
        self.data.manager = new_manager

    @sp.entry_point
    def add_fa2(self, fa2):
        """Adds a new FA2 token address to the list of tradable tokens.

        """
        # Define the input parameter data type
        sp.set_type(fa2, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Add the new FA2 token address
        self.data.allowed_fa2s[fa2] = True

    @sp.entry_point
    def remove_fa2(self, fa2):
        """Removes one of the tradable FA2 token address.

        """
        # Define the input parameter data type
        sp.set_type(fa2, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Dissable the FA2 token address
        self.data.allowed_fa2s[fa2] = False

    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
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
                    token_id=token_id,
                    amount=token_amount)]))]),
            amount=sp.mutez(0),
            destination=c)


# Add a compilation target initialized to a test account and the OBJKT FA2 contract
sp.add_compilation_target("marketplace", Marketplace(
    manager=sp.address("tz1gnL9CeM5h5kRzWZztFYLypCNnVQZjndBN"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    allowed_fa2s=sp.big_map({sp.address("KT1RJ6PbjHpwc3M5rw5s2Nbmefwbuwbdxton"): True}),
    fee=sp.nat(25)))
