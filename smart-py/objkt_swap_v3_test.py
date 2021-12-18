"""Unit tests for the Marketplace v3 class.

"""

import smartpy as sp
import os

# Import the FA2 and marketplaces modules
fa2Contract = sp.io.import_script_from_url(f"file://{os.getcwd()}/fa2.py")
# for minting
marketplaceContractV1 = sp.io.import_script_from_url(f"file://{os.getcwd()}/objkt_swap_v1.py")
# for swapping
marketplaceContractV3 = sp.io.import_script_from_url(f"file://{os.getcwd()}/objkt_swap_v3.py")


def get_test_environment():
    # Create the test accounts
    admin = sp.test_account("admin")
    artist1 = sp.test_account("artist1")
    artist2 = sp.test_account("artist2")
    collector1 = sp.test_account("collector1")
    collector2 = sp.test_account("collector2")

    # Initialize the OBJKT contract
    objkt = fa2Contract.FA2(
        config=fa2Contract.FA2_config(),
        admin=admin.address,
        meta=sp.utils.metadata_of_url("ipfs://aaa"))

    # Initialize the hDAO contract
    hdao = fa2Contract.FA2(
        config=fa2Contract.FA2_config(),
        admin=admin.address,
        meta=sp.utils.metadata_of_url("ipfs://bbb"))

    # Initialize the new OBJKT contract
    newobjkt = fa2Contract.FA2(
        config=fa2Contract.FA2_config(),
        admin=admin.address,
        meta=sp.utils.metadata_of_url("ipfs://ccc"))

    # Initialize a dummy curate contract
    curate = sp.Contract()

    # Initialize the marketplace v1 contract
    marketplaceV1 = marketplaceContractV1.OBJKTSwap(
        objkt=objkt.address,
        hdao=hdao.address,
        manager=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ddd"),
        curate=curate.address)

    # Initialize the marketplace v3 contract
    marketplaceV3 = marketplaceContractV3.Marketplace(
        manager=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://eee"),
        allowed_fa2s=sp.big_map({objkt.address: True}),
        fee=25)

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += objkt
    scenario += hdao
    scenario += newobjkt
    scenario += curate
    scenario += marketplaceV1
    scenario += marketplaceV3

    # Change the OBJKT token administrator to the marketplace v1 contract
    scenario += objkt.set_administrator(marketplaceV1.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "admin" : admin,
        "artist1" : artist1,
        "artist2" : artist2,
        "collector1" : collector1,
        "collector2" : collector2,
        "objkt" : objkt,
        "hdao" : hdao,
        "newobjkt" : newobjkt,
        "curate" : curate,
        "marketplaceV1" : marketplaceV1,
        "marketplaceV3" : marketplaceV3}

    return testEnvironment


@sp.add_test(name="Test swap and collect")
def test_swap_and_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # should be correct genesis number
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # Mint an OBJKT
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # objkt number must have been incremented by 1
    scenario.verify(marketplaceV1.data.objkt_id == 153)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Check that there is are no swaps before
    scenario.verify(~marketplaceV3.data.swaps.contains(0))
    scenario.verify(~marketplaceV3.has_swap(0))
    scenario.verify(marketplaceV3.data.counter == 0)

    swapped_editions = 50
    edition_price = 1000000
    royalties = 100

    # Swap more than exist and fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=editions + 1,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)

    # No tez allowed
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1, amount=sp.tez(3))

    # Swap one OBJKT in the marketplace v3 contract
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions)
    scenario.verify(marketplaceV3.data.counter == 1)

    # Check that the swaps big map is correct
    scenario.verify(marketplaceV3.data.swaps.contains(0))
    scenario.verify(marketplaceV3.data.swaps[0].issuer == artist1.address)
    scenario.verify(marketplaceV3.data.swaps[0].fa2 == objkt.address)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_id == objkt_id)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions)
    scenario.verify(marketplaceV3.data.swaps[0].xtz_per_objkt == sp.mutez(edition_price))
    scenario.verify(marketplaceV3.data.swaps[0].royalties == royalties)
    scenario.verify(marketplaceV3.data.swaps[0].creator == artist1.address)

    # Check that the on-chain views work
    scenario.verify(marketplaceV3.has_swap(0))
    scenario.verify(marketplaceV3.get_swap(0).issuer == artist1.address)
    scenario.verify(marketplaceV3.get_swap(0).fa2 == objkt.address)
    scenario.verify(marketplaceV3.get_swap(0).objkt_id == objkt_id)
    scenario.verify(marketplaceV3.get_swap(0).objkt_amount == swapped_editions)
    scenario.verify(marketplaceV3.get_swap(0).xtz_per_objkt == sp.mutez(edition_price))
    scenario.verify(marketplaceV3.get_swap(0).royalties == royalties)
    scenario.verify(marketplaceV3.get_swap(0).creator == artist1.address)

    # Check that collecting fails if the collector is the swap issuer
    scenario += marketplaceV3.collect(0).run(valid=False, sender=artist1, amount=sp.mutez(edition_price))

    # Check that collecting fails if the exact tez amount is not provided
    scenario += marketplaceV3.collect(0).run(valid=False, sender=collector1, amount=sp.mutez(edition_price - 1))
    scenario += marketplaceV3.collect(0).run(valid=False, sender=collector1, amount=sp.mutez(edition_price + 1))

    # Collect the OBJKT with two different collectors
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.collect(0).run(sender=collector2, amount=sp.mutez(edition_price))

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplaceV3.balance == sp.mutez(0))
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions - 2)
    scenario.verify(marketplaceV3.get_swap(0).objkt_amount == swapped_editions - 2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions - 2)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)
    scenario.verify(objkt.data.ledger[(collector2.address, objkt_id)].balance == 1)

    # Check that only the swapper can cancel the swap
    scenario += marketplaceV3.cancel_swap(0).run(valid=False, sender=collector1)
    scenario += marketplaceV3.cancel_swap(0).run(valid=False, sender=artist1, amount=sp.tez(3))
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - 2)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == 0)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)
    scenario.verify(objkt.data.ledger[(collector2.address, objkt_id)].balance == 1)

    # Check that the swaps big map has been updated
    scenario.verify(~marketplaceV3.data.swaps.contains(0))
    scenario.verify(~marketplaceV3.has_swap(0))

    # Check that the swap cannot be cancelled twice
    scenario += marketplaceV3.cancel_swap(0).run(valid=False, sender=artist1)


@sp.add_test(name="Test free collect")
def test_free_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Swap the OBJKT in the marketplace v3 contract
    swapped_editions = 50
    edition_price = 0
    royalties = 100
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Correct amount
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplaceV3.balance == sp.mutez(0))
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions - 1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions - 1)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)


@sp.add_test(name="Test very cheap collect")
def test_very_cheap_collect():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Swap the OBJKT in the marketplace v3 contract
    swapped_editions = 50
    edition_price = 2
    royalties = 100
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplaceV3.balance == sp.mutez(0))
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions - 1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions - 1)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)


@sp.add_test(name="Test update fee")
def test_update_fee():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Check the original fee
    scenario.verify(marketplaceV3.data.fee == 25)
    scenario.verify(marketplaceV3.get_fee() == 25)

    # Check that only the admin can update the fees
    new_fee = 100
    scenario += marketplaceV3.update_fee(new_fee).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_fee(new_fee).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.update_fee(new_fee).run(sender=admin)

    # Check that the fee is updated
    scenario.verify(marketplaceV3.data.fee == new_fee)
    scenario.verify(marketplaceV3.get_fee() == new_fee)

    # Check that if fails if we try to set a fee that its too high
    new_fee = 1000
    scenario += marketplaceV3.update_fee(new_fee).run(valid=False, sender=admin)


@sp.add_test(name="Test update fee recipient")
def test_update_fee_recipient():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Check the original fee recipient
    scenario.verify(marketplaceV3.data.fee_recipient == admin.address)
    scenario.verify(marketplaceV3.get_fee_recipient() == admin.address)

    # Check that only the admin can update the fee recipient
    new_fee_recipient = artist1.address
    scenario += marketplaceV3.update_fee_recipient(new_fee_recipient).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_fee_recipient(new_fee_recipient).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.update_fee_recipient(new_fee_recipient).run(sender=admin)

    # Check that the fee recipient is updated
    scenario.verify(marketplaceV3.data.fee_recipient == new_fee_recipient)
    scenario.verify(marketplaceV3.get_fee_recipient() == new_fee_recipient)


@sp.add_test(name="Test update manager")
def test_update_manager():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Check the original manager
    scenario.verify(marketplaceV3.data.manager == admin.address)
    scenario.verify(marketplaceV3.get_manager() == admin.address)

    # Check that only the admin can update the manager
    new_manager = artist1.address
    scenario += marketplaceV3.update_manager(new_manager).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_manager(new_manager).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.update_manager(new_manager).run(sender=admin)

    # Check that the manager is updated
    scenario.verify(marketplaceV3.data.manager == new_manager)

    # Check that only the new manager can update the manager
    new_manager = artist2.address
    scenario += marketplaceV3.update_manager(new_manager).run(valid=False, sender=admin)
    scenario += marketplaceV3.update_manager(new_manager).run(sender=artist1)

    # Check that the manager is updated
    scenario.verify(marketplaceV3.data.manager == new_manager)
    scenario.verify(marketplaceV3.get_manager() == new_manager)


@sp.add_test(name="Test update metadata")
def test_update_metadata():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Check that only the admin can update the metadata
    new_metadata = sp.record(key="", value=sp.pack("ipfs://zzzz"))
    scenario += marketplaceV3.update_metadata(new_metadata).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_metadata(new_metadata).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.update_metadata(new_metadata).run(sender=admin)

    # Check that the metadata is updated
    scenario.verify(marketplaceV3.data.metadata[new_metadata.key] == new_metadata.value)

    # Add some extra metadata
    extra_metadata = sp.record(key="aaa", value=sp.pack("ipfs://ffff"))
    scenario += marketplaceV3.update_metadata(extra_metadata).run(sender=admin)

    # Check that the two metadata entries are present
    scenario.verify(marketplaceV3.data.metadata[new_metadata.key] == new_metadata.value)
    scenario.verify(marketplaceV3.data.metadata[extra_metadata.key] == extra_metadata.value)


@sp.add_test(name="Test add and remove fa2")
def test_add_and_remove_fa2():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    newobjkt = testEnvironment["newobjkt"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint a newOBJKTs
    objkt_id = 0
    editions = 100
    newobjkt.mint(
        address=artist1.address,
        amount=editions,
        token_id=objkt_id,
        token_info={"" : sp.utils.bytes_of_string("ipfs://ccc")}).run(sender=admin)

    # Add the marketplace contract as an operator to be able to swap it
    scenario += newobjkt.update_operators(
        [sp.variant("add_operator", newobjkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Check that is not possible to swap this token
    swapped_editions = 50
    edition_price = 1000000
    royalties = 100
    scenario += marketplaceV3.swap(
        fa2=newobjkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)

    # Check the view mode
    scenario.verify(marketplaceV3.is_allowed_fa2(objkt.address))
    scenario.verify(~marketplaceV3.is_allowed_fa2(newobjkt.address))

    # Check that only the admin can update the fa2 list
    new_fa2 = newobjkt.address
    scenario += marketplaceV3.add_fa2(new_fa2).run(valid=False, sender=artist1)
    scenario += marketplaceV3.add_fa2(new_fa2).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.add_fa2(new_fa2).run(sender=admin)

    # Check that the new FA2 token is now part of the allowed FA2 contracts
    scenario.verify(marketplaceV3.data.allowed_fa2s[objkt.address])
    scenario.verify(marketplaceV3.data.allowed_fa2s[new_fa2])
    scenario.verify(marketplaceV3.is_allowed_fa2(objkt.address))
    scenario.verify(marketplaceV3.is_allowed_fa2(new_fa2))

    # Check that now is possible to swap the newOBJKT
    scenario += marketplaceV3.swap(
        fa2=newobjkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Check that the newOBJKT ledger information is correct
    scenario.verify(newobjkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(newobjkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions)

    # Check that the swaps big map is correct
    scenario.verify(marketplaceV3.data.swaps.contains(0))
    scenario.verify(marketplaceV3.data.swaps[0].issuer == artist1.address)
    scenario.verify(marketplaceV3.data.swaps[0].fa2 == newobjkt.address)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_id == objkt_id)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions)
    scenario.verify(marketplaceV3.data.swaps[0].xtz_per_objkt == sp.mutez(edition_price))
    scenario.verify(marketplaceV3.data.swaps[0].royalties == royalties)
    scenario.verify(marketplaceV3.data.swaps[0].creator == artist1.address)

    # Remove the newOBJKT token from the allowed fa2 list
    scenario += marketplaceV3.remove_fa2(newobjkt.address).run(valid=False, sender=artist1)
    scenario += marketplaceV3.remove_fa2(newobjkt.address).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.remove_fa2(newobjkt.address).run(sender=admin)

    # Check that now is not allowed to trade newOBJKT tokens
    scenario.verify(marketplaceV3.data.allowed_fa2s[objkt.address])
    scenario.verify(~marketplaceV3.data.allowed_fa2s[newobjkt.address])
    scenario.verify(marketplaceV3.is_allowed_fa2(objkt.address))
    scenario.verify(~marketplaceV3.is_allowed_fa2(newobjkt.address))
    scenario += marketplaceV3.swap(
        fa2=newobjkt.address,
        objkt_id=objkt_id,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)

    # Check that however it is still possible to collect the previous swap and to cancel it
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Check that the newOBJKT ledger information is correct
    scenario.verify(newobjkt.data.ledger[(artist1.address, objkt_id)].balance == editions - 1)
    scenario.verify(newobjkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == 0)
    scenario.verify(newobjkt.data.ledger[(collector1.address, objkt_id)].balance == 1)

@sp.add_test(name="Test pause swaps")
def test_pause_swaps():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Swap one OBJKT in the marketplace v3 contract
    swapped_editions = 10
    edition_price = 1000000
    royalties = 100
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))

    # Pause the swaps
    scenario += marketplaceV3.pause_swaps(True).run(valid=False, sender=collector1)
    scenario += marketplaceV3.pause_swaps(True).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.pause_swaps(True).run(sender=admin)

    # Check that only the swaps are paused
    scenario.verify(marketplaceV3.data.swaps_paused)
    scenario.verify(~marketplaceV3.data.collects_paused)

    # Check that swapping is not allowed
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)

    # Check that collecting is still allowed
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))

    # Check that cancel swaps are still allowed
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Unpause the swaps again
    scenario += marketplaceV3.pause_swaps(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)
    scenario += marketplaceV3.collect(1).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.cancel_swap(1).run(sender=artist1)

@sp.add_test(name="Test pause collects")
def test_pause_collects():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Swap one OBJKT in the marketplace v3 contract
    swapped_editions = 10
    edition_price = 1000000
    royalties = 100
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))

    # Pause the collects
    scenario += marketplaceV3.pause_collects(True).run(valid=False, sender=collector1)
    scenario += marketplaceV3.pause_collects(True).run(valid=False, sender=admin, amount=sp.tez(3))
    scenario += marketplaceV3.pause_collects(True).run(sender=admin)

    # Check that only the collects are paused
    scenario.verify(~marketplaceV3.data.swaps_paused)
    scenario.verify(marketplaceV3.data.collects_paused)

    # Check that collecting is not allowed
    scenario += marketplaceV3.collect(0).run(valid=False, sender=collector1, amount=sp.mutez(edition_price))

    # Check that swapping is still allowed
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)

    # Check that cancel swaps are still allowed
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Unpause the collects again
    scenario += marketplaceV3.pause_collects(False).run(sender=admin)

    # Check that swapping and collecting is possible again
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)
    scenario += marketplaceV3.collect(2).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.cancel_swap(2).run(sender=artist1)

@sp.add_test(name="Test mint failure conditions")
def test_mint_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # should be correct genesis number
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # Mint an OBJKT but with 0 copies
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=0,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1,valid=False)

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # Mint an OBJKT but with too many copies
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100000,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1,valid=False)

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # no royalties were injected
    scenario.verify(marketplaceV1.data.royalties.contains(152) == False)

    # try to mint an objkt on behalf of someone else and fail
    scenario += marketplaceV1.mint_OBJKT(
        address = artist1.address,
        amount = 1,
        royalties = 200,
        # how to turn json into this?
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = collector1.address,
        valid = False
    )

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # try to mint an objkt with too many royalties
    scenario += marketplaceV1.mint_OBJKT(
        address = artist1.address,
        amount = 2,
        royalties = 300,
        metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    ).run(
        sender = artist1.address,
        valid = False
    )

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # try to mint an objkt with too few royalties
    # TODO should fail but passes currently
    # scenario += marketplaceV1.mint_OBJKT(
    #     address = artist1.address,
    #     amount = 2,
    #     royalties = 5,
    #     metadata = sp.bytes('0x697066733a2f2f516d61794e7a7258547a354237577747574868314459524c7869646646504676775a377a364b7443377268456468')
    # ).run(
    #     sender = artist1.address,
    #     valid = False
    # )

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # try to mint without metadata and fail
    #
    # TODO null metadata should fail but passes currently
    #
    # scenario += marketplaceV1.mint_OBJKT(
    #     address = artist1.address,
    #     amount = 1,
    #     royalties = 200,
    #     metadata = sp.bytes('0x00')
    # ).run(
    #     sender = artist1.address,
    #     valid = False
    # )

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)

@sp.add_test(name="Test swap v3 failure conditions")
def test_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # fail to mint an OBJKT on behalf of someone else
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=1,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        valid=False,
        sender=artist2
    )

    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # fail to mint an OBJKT on behalf of someone else as admin
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=1,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        valid=False,
        sender=admin
    )

    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=1,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        sender=artist1
    )

    scenario.verify(marketplaceV1.data.objkt_id == 153)

    # Try to Swap the OBJKT but fail because artist is not admin
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        valid=False,
        sender=artist1
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # Artist updates the objkt to be managed by marketplace v3
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)

    # Try to Swap the OBJKT as someone else with a different creator must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist2.address
    ).run(
        valid=False,
        sender=artist2
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # Try to Swap the OBJKT as someone else with the same creator must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        valid=False,
        sender=artist2
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # Try to Swap the OBJKT as the artist with a different creator must fail
    #
    # TODO a holder can swap a piece with a different creator, how to verify
    # the creator is the true creator?
    #
    # Possible royalty redirection attack vector
    #
    # scenario += marketplaceV3.swap(
    #     fa2=objkt.address,
    #     objkt_id=152,
    #     objkt_amount=1,
    #     xtz_per_objkt=sp.mutez(10000),
    #     royalties=100,
    #     creator=artist2.address
    # ).run(
    #     valid=False,
    #     sender=artist1
    # )
    #
    # # No swap was added
    # scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    # scenario.verify(marketplaceV3.data.counter == 0)

    # trying to swap more editions than are available must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=False
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # trying to swap someone elses objkt must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist2,
        valid=False
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # trying to swap someone elses objkt as admin must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=admin,
        valid=False
    )

    # trying to swap someone elses objkt with unusual body must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # No swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # Cannot swap 0 items
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=0,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=False
    )

    # swap was not added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.counter == 0)

    # Successfully swap
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=True
    )

    # swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # second swap should now fail because there is only 1 edition available
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=False
    )

    # no swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # Mint a multi edition from a second OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist2.address,
        amount=10,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        sender=artist2
    )

    # objkt was added
    scenario.verify(marketplaceV1.data.objkt_id == 154)

    # Artist 2 updates the new objkt to be managed by marketplace v3
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist2.address,
            operator=marketplaceV3.address,
            token_id=153))]).run(sender=artist2)

    # Fail to swap second objkt as second artist when royalty mismatch
    #
    # TODO this should fail because there is a royalty mismatch
    # and no swap should be added in this instance
    #
    # scenario += marketplaceV3.swap(
    #     fa2=objkt.address,
    #     objkt_id=153,
    #     objkt_amount=10,
    #     xtz_per_objkt=sp.mutez(12000),
    #     royalties=200,
    #     creator=artist2.address
    # ).run(
    #     sender=artist2,
    #     valid=False
    # )
    #
    # # swap was not added
    # scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    # scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    # scenario.verify(marketplaceV3.data.counter == 1)

    # Fail to swap low royalties
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=153,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(12000),
        royalties=5,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # # swap was not added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # Fail to swap zero royalties
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=153,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(12000),
        royalties=0,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # # swap was not added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # Fail to swap second objkt as second artist when too many editions
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=153,
        objkt_amount=100,
        xtz_per_objkt=sp.mutez(12000),
        royalties=100,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # swap was not added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # trying to swap a token id that doesn't exist yet must fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=154,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(12000),
        royalties=100,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # swap was not added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # Successfully swap second objkt as artist
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=153,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(12000),
        royalties=100,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=True
    )

    # swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(2) == False)
    scenario.verify(marketplaceV3.data.counter == 2)

    # try to double swap second objkt and fail
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=153,
        objkt_amount=10,
        xtz_per_objkt=sp.mutez(12000),
        royalties=100,
        creator=artist2.address
    ).run(
        sender=artist2,
        valid=False
    )

    # no swap was added
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(2) == False)
    scenario.verify(marketplaceV3.data.counter == 2)

@sp.add_test(name="Test cancel v3 swap failure conditions")
def test_cancel_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=1,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        sender=artist1
    )

    # Artist updates the objkt to be managed by marketplace v3
    editions = 100
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=editions,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Add the marketplace contract as an operator to be able to swap it
    objkt_id = 152
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Successfully swap
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(10000),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=True
    )

    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # try cancel nonexistent
    scenario += marketplaceV3.cancel_swap(1535).run(
        sender = artist1,
        valid = False
    )

    # first one still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # try cancel someone elses
    scenario += marketplaceV3.cancel_swap(0).run(
        sender = artist2,
        valid = False
    )

    # first one still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # try cancel someone elses as admin
    scenario += marketplaceV3.cancel_swap(0).run(
        sender = admin,
        valid = False
    )

    # first one still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # cancel own swap successfully
    scenario += marketplaceV3.cancel_swap(0).run(
        sender = artist1,
        valid = True
    )

    # swap is gone
    scenario.verify(marketplaceV3.data.swaps.contains(0) == False)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)

    # but id still incremented
    scenario.verify(marketplaceV3.data.counter == 1)

@sp.add_test(name="Test collect v3 swap failure conditions")
def test_collect_swap_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=1,
        metadata=sp.pack("ipfs://fff"),
        royalties=100
    ).run(
        sender=artist1
    )

    # Artist updates the objkt to be managed by marketplace v3
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)

    # Fail to swap someone elses
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(1),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=admin,
        valid=False
    )

    # Successfully swap
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(1),
        royalties=100,
        creator=artist1.address
    ).run(
        sender=artist1,
        valid=True
    )

    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == 1)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # try to collect nonexistent swap and fail
    scenario += marketplaceV3.collect(100).run(
        sender = collector1,
        amount = sp.mutez(1),
        valid = False
    )

    # first one still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == 1)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # try to collect own swap and fail
    scenario += marketplaceV3.collect(0).run(
        sender = artist1,
        amount = sp.mutez(1),
        valid = False
    )

    # # first one still exists
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == 1)

    # this should fail because amount is wrong
    scenario += marketplaceV3.collect(0).run(
        sender = collector1,
        amount = sp.mutez(100),
        valid = False
    )

    # first one still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == 1)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # this should pass
    scenario += marketplaceV3.collect(0).run(
        sender = collector1,
        amount = sp.mutez(1),
        valid = True
    )

    # swap entry still exists
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    # except there are no copies left
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == 0)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)

    # this should fail now
    scenario += marketplaceV3.collect(0).run(
        sender = collector1,
        amount = sp.mutez(1),
        valid = False
    )

    # swap hasn't changed
    scenario.verify(marketplaceV3.data.swaps.contains(0) == True)
    scenario.verify(marketplaceV3.data.swaps.get(0).objkt_amount == 0)
    scenario.verify(marketplaceV3.data.swaps.contains(1) == False)
    scenario.verify(marketplaceV3.data.counter == 1)
