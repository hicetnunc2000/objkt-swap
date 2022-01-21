"""The HEN Community marketplace contract.

This version corrects several small bugs from the v2 H=N marketplace contract
and adds the possibility to trade different kinds of FA2 tokens.


Error message codes:

- HENC_NOT_MANAGER: The operation can only be executed by the contract manager.
- HENC_TEZ_TRANSFER: The operation does not require tez transfers.
- HENC_SWAPS_PAUSED: Swaps are currently paused in the marketplace.
- HENC_COLLECTS_PAUSED: Collects are currently paused in the marketplace.
- HENC_FA2_NOT_ALLOWED: This FA2 token cannot cannot be traded in the marketplace.
- HENC_NO_SWAPPED_EDITIONS: At least one edition needs to be swapped.
- HENC_WRONG_ROYALTIES: The royalties cannot be higher than 25%.
- HENC_WRONG_SWAP_ID: The swap_id doesn't exist.
- HENC_IS_SWAP_ISSUER: The collector cannot be the swap issuer.
- HENC_WRONG_TEZ_AMOUNT: The sent tez amount does not coincide with the edition price.
- HENC_SWAP_COLLECTED: All the swapped editions have already been collected.
- HENC_NOT_SWAP_ISSUER: Only the swap issuer can cancel the swap.
- HENC_WRONG_FEES: The marketplace fees cannot be higher than 25%.
- HENC_NO_NEW_MANAGER: The new manager has not been proposed.
- HENC_NOT_PROPOSED_MANAGER: The operation can only be executed by the proposed manager.

"""

import smartpy as sp


class Marketplace(sp.Contract):
    """This contract implements the first version of the HEN Community
    marketplace contract.

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

        Parameters
        ----------
        manager: sp.TAddress
            The initial marketplace manager address. It could be a tz or KT
            address.
        metadata: sp.TBigMap(sp.TString, sp.TBytes)
            The contract metadata big map. It should contain the IPFS path to
            the contract metadata json file.
        allowed_fa2s: sp.TBigMap(sp.TAddress, sp.TBool)
            A big map with the list FA2 token addresses that can be traded (or
            not) in the marketplace.
        fee: sp.TNat
            The marketplace fee in per mille units (25 = 2.5%).

        """
        # Define the contract storage data types for clarity
        self.init_type(sp.TRecord(
            # The contract manager. It could be a tz or KT address.
            manager=sp.TAddress,
            # The contract metadata bigmap.
            # The metadata is stored as a json file in IPFS and the big map
            # contains the IPFS path.
            metadata=sp.TBigMap(sp.TString, sp.TBytes),
            # The big map with the FA2 token addresses that can be traded (or
            # not) in the marketplace.
            allowed_fa2s=sp.TBigMap(sp.TAddress, sp.TBool),
            # The big map with the swaps information.
            swaps=sp.TBigMap(sp.TNat, Marketplace.SWAP_TYPE),
            # The marketplace fee taken for each collect operation in per mille
            # units (25 = 2.5%).
            fee=sp.TNat,
            # The address that will receive the marketplace fees. It could be
            # a tz or KT address.
            fee_recipient=sp.TAddress,
            # The swaps bigmap counter. It tracks the total number of swaps in
            # the swaps big map.
            counter=sp.TNat,
            # The proposed new manager address. Only set when a new manager is
            # proposed.
            proposed_manager=sp.TOption(sp.TAddress),
            # A flag that indicates if the marketplace swaps are paused or not.
            swaps_paused=sp.TBool,
            # A flag that indicates if the marketplace collects are paused or not.
            collects_paused=sp.TBool))

        # Initialize the contract storage
        self.init(
            manager=manager,
            metadata=metadata,
            allowed_fa2s=allowed_fa2s,
            swaps=sp.big_map(),
            fee=fee,
            fee_recipient=manager,
            counter=0,
            proposed_manager=sp.none,
            swaps_paused=False,
            collects_paused=False)

    def check_is_manager(self):
        """Checks that the address that called the entry point is the contract
        manager.

        """
        sp.verify(sp.sender == self.data.manager, message="HENC_NOT_MANAGER")

    def check_no_tez_transfer(self):
        """Checks that no tez were transferred in the operation.

        """
        sp.verify(sp.amount == sp.tez(0), message="HENC_TEZ_TRANSFER")

    @sp.entry_point
    def swap(self, params):
        """Swaps several editions of a token for a fixed price.

        Parameters
        ----------
        params: sp.TRecord
            The swap parameters:
            - fa2: the FA2 token contract address.
            - objkt_id: the OBJKT id.
            - objkt_amount: the number of editions to swap.
            - xtz_per_objkt: the price per edition in mutez.
            - royalties: the artist/creator royalties in per mille units.
            - creator: the artist/creator address. It could be a KT address for
              artists collaborations.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            fa2=sp.TAddress,
            objkt_id=sp.TNat,
            objkt_amount=sp.TNat,
            xtz_per_objkt=sp.TMutez,
            royalties=sp.TNat,
            creator=sp.TAddress).layout(
                ("fa2", ("objkt_id", ("objkt_amount", ("xtz_per_objkt", ("royalties", "creator")))))))

        # Check that swaps are not paused
        sp.verify(~self.data.swaps_paused, message="HENC_SWAPS_PAUSED")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the token is one of the allowed tokens to trade
        sp.verify(self.data.allowed_fa2s.get(params.fa2, default_value=False),
                  message="HENC_FA2_NOT_ALLOWED")

        # Check that at least one edition will be swapped
        sp.verify(params.objkt_amount > 0, message="HENC_NO_SWAPPED_EDITIONS")

        # Check that the royalties are within the expected limits
        sp.verify(params.royalties <= 250, message="HENC_WRONG_ROYALTIES")

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

        Parameters
        ----------
        swap_id: sp.TNat
            The swap id. It refers to the swaps big map key containing the swap
            parameters.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that collects are not paused
        sp.verify(~self.data.collects_paused, message="HENC_COLLECTS_PAUSED")

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id),
                  message="HENC_WRONG_SWAP_ID")

        # Check that the collector is not the creator of the swap
        swap = self.data.swaps[swap_id]
        sp.verify(sp.sender != swap.issuer, message="HENC_IS_SWAP_ISSUER")

        # Check that the provided tez amount is exactly the edition price
        sp.verify(sp.amount == swap.xtz_per_objkt,
                  message="HENC_WRONG_TEZ_AMOUNT")

        # Check that there is at least one edition available to collect
        sp.verify(swap.objkt_amount > 0, message="HENC_SWAP_COLLECTED")

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

        Parameters
        ----------
        swap_id: sp.TNat
            The swap id. It refers to the swaps big map key containing the swap
            parameters.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id),
                  message="HENC_WRONG_SWAP_ID")

        # Check that the swap issuer is cancelling the swap
        swap = self.data.swaps[swap_id]
        sp.verify(sp.sender == swap.issuer, message="HENC_NOT_SWAP_ISSUER")

        # Check that there is at least one swapped edition
        sp.verify(swap.objkt_amount > 0, message="HENC_SWAP_COLLECTED")

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

        Parameters
        ----------
        new_fee: sp.TNat
            The new marketplace fee in per mille units (25 = 2.5%).

        """
        # Define the input parameter data type
        sp.set_type(new_fee, sp.TNat)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Check that the new fee is not larger than 25%
        sp.verify(new_fee <= 250, message="HENC_WRONG_FEES")

        # Set the new management fee
        self.data.fee = new_fee

    @sp.entry_point
    def update_fee_recipient(self, new_fee_recipient):
        """Updates the marketplace management fee recipient address.

        Parameters
        ----------
        new_fee_recipient: sp.TAddress
            The new address that will receive the marketplace fees. It could be
            a tz or KT address.

        """
        # Define the input parameter data type
        sp.set_type(new_fee_recipient, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new management fee recipient address
        self.data.fee_recipient = new_fee_recipient

    @sp.entry_point
    def transfer_manager(self, proposed_manager):
        """Proposes to transfer the marketplace manager to another address.

        Parameters
        ----------
        proposed_manager: sp.TAddress
            The address of the proposed new marketplace manager. It could be a
            tz or KT address.

        """
        # Define the input parameter data type
        sp.set_type(proposed_manager, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new proposed manager address
        self.data.proposed_manager = sp.some(proposed_manager)

    @sp.entry_point
    def accept_manager(self):
        """The proposed manager accepts the marketplace manager
        responsabilities.

        """
        # Check that there is a proposed manager
        sp.verify(self.data.proposed_manager.is_some(),
                  message="HENC_NO_NEW_MANAGER")

        # Check that the proposed manager executed the entry point
        sp.verify(sp.sender == self.data.proposed_manager.open_some(),
                  message="HENC_NOT_PROPOSED_MANAGER")

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Set the new manager address
        self.data.manager = sp.sender

        # Reset the proposed manager value
        self.data.proposed_manager = sp.none

    @sp.entry_point
    def update_metadata(self, params):
        """Updates the contract metadata.

        Parameters
        ----------
        params: sp.TRecord
            The updated metadata parameters:
            - key: the metadata big map key to update.
            - value: the IPFS path to the json file with the updated metadata.

        """
        # Define the input parameter data type
        sp.set_type(params, sp.TRecord(
            key=sp.TString,
            value=sp.TBytes).layout(("key", "value")))

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Update the contract metadata
        self.data.metadata[params.key] = params.value

    @sp.entry_point
    def add_fa2(self, fa2):
        """Adds a new FA2 token address to the list of tradable tokens.

        Parameters
        ----------
        fa2: sp.TAddress
            The FA2 token contract address to trade.

        """
        # Define the input parameter data type
        sp.set_type(fa2, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Add the new FA2 token address
        self.data.allowed_fa2s[fa2] = True

    @sp.entry_point
    def remove_fa2(self, fa2):
        """Removes one of the tradable FA2 token address.

        Parameters
        ----------
        fa2: sp.TAddress
            The FA2 token contract address to remove.

        """
        # Define the input parameter data type
        sp.set_type(fa2, sp.TAddress)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Disable the FA2 token address
        self.data.allowed_fa2s[fa2] = False

    @sp.entry_point
    def pause_swaps(self, pause):
        """Pause or not the swaps.

        Parameters
        ----------
        pause: sp.TBool
            If true, swaps will be paused in the marketplace. False will allow
            to create new swaps again.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the swaps
        self.data.swaps_paused = pause

    @sp.entry_point
    def pause_collects(self, pause):
        """Pause or not the collects.

        Parameters
        ----------
        pause: sp.TBool
            If true, collects will be paused in the marketplace. False will
            allow to collect again.

        """
        # Define the input parameter data type
        sp.set_type(pause, sp.TBool)

        # Check that the manager executed the entry point
        self.check_is_manager()

        # Check that no tez have been transferred
        self.check_no_tez_transfer()

        # Pause or unpause the collects
        self.data.collects_paused = pause

    @sp.onchain_view()
    def get_manager(self):
        """Returns the marketplace manager address.

        Returns
        -------
        sp.TAddress
            The marketplace manager address.

        """
        sp.result(self.data.manager)

    @sp.onchain_view()
    def is_allowed_fa2(self, fa2):
        """Checks if a given FA2 token contract can be traded in the
        marketplace.

        Parameters
        ----------
        fa2: sp.TAddress
            The FA2 token contract address.

        Returns
        -------
        sp.TBool
            True, if the token can be traded in the marketplace.

        """
        # Define the input parameter data type
        sp.set_type(fa2, sp.TAddress)

        # Return if it can be traded or not
        sp.result(self.data.allowed_fa2s.get(fa2, default_value=False))

    @sp.onchain_view()
    def has_swap(self, swap_id):
        """Check if a given swap id is present in the swaps big map.

        Parameters
        ----------
        swap_id: sp.TNat
            The swap id.

        Returns
        -------
        sp.TBool
            True, if there is a swap with the provided id.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Return True if the swap id is present in the swaps big map
        sp.result(self.data.swaps.contains(swap_id))

    @sp.onchain_view()
    def get_swap(self, swap_id):
        """Returns the complete information from a given swap id.

        Parameters
        ----------
        swap_id: sp.TNat
            The swap id.

        Returns
        -------
        sp.TRecord
            The swap parameters:
            - issuer: the swap issuer address.
            - fa2: the FA2 token contract address.
            - objkt_id: the OBJKT id.
            - objkt_amount: the number of currently swapped editions.
            - xtz_per_objkt: the price per edition in mutez.
            - royalties: the artist/creator royalties in per mille units.
            - creator: the artist/creator address.

        """
        # Define the input parameter data type
        sp.set_type(swap_id, sp.TNat)

        # Check that the swap id is present in the swaps big map
        sp.verify(self.data.swaps.contains(swap_id),
                  message="HENC_WRONG_SWAP_ID")

        # Return the swap information
        sp.result(self.data.swaps[swap_id])

    @sp.onchain_view()
    def get_swaps_counter(self):
        """Returns the swaps counter.

        Returns
        -------
        sp.TNat
            The total number of swaps.

        """
        sp.result(self.data.counter)

    @sp.onchain_view()
    def get_fee(self):
        """Returns the marketplace fee.

        Returns
        -------
        sp.TNat
            The marketplace fee in per mille units.

        """
        sp.result(self.data.fee)

    @sp.onchain_view()
    def get_fee_recipient(self):
        """Returns the marketplace fee recipient address.

        Returns
        -------
        sp.TAddress
            The address that receives the marketplace fees.

        """
        sp.result(self.data.fee_recipient)

    def fa2_transfer(self, fa2, from_, to_, token_id, token_amount):
        """Transfers a number of editions of a FA2 token between two addresses.

        Parameters
        ----------
        fa2: sp.TAddress
            The FA2 token contract address.
        from_: sp.TAddress
            The address from which the tokens will be transferred.
        to_: sp.TAddress
            The address that will receive the tokens.
        token_id: sp.TNat
            The token id.
        token_amount: sp.TNat
            The number of token editions to transfer.

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


# Add a compilation target initialized to a test account and the test OBJKT FA2 contract
sp.add_compilation_target("marketplace", Marketplace(
    manager=sp.address("tz1gnL9CeM5h5kRzWZztFYLypCNnVQZjndBN"),
    metadata=sp.utils.metadata_of_url("ipfs://aaa"),
    allowed_fa2s=sp.big_map({sp.address("KT1QZhpqLNjoKM21mGuDo6ygE3NajEXKFHp9"): True}),
    fee=sp.nat(25)))
