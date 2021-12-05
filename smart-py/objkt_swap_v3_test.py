"""Unit tests for the Marketplace v3 class.

"""

import smartpy as sp

# Import the FA2 and marketplaces modules
fa2Contract = sp.io.import_script_from_url("file:smart-py/fa2.py")
marketplaceContractV1 = sp.io.import_script_from_url("file:smart-py/objkt_swap_v1.py")
marketplaceContractV3 = sp.io.import_script_from_url("file:smart-py/objkt_swap_v3.py")


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
    scenario += newobjkt
    scenario += hdao
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
    artist2 = testEnvironment["artist2"]
    collector1 = testEnvironment["collector1"]
    collector2 = testEnvironment["collector2"]
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

    # Swap one OBJKT in the marketplace v3 contract
    objkt_id = 152
    swapped_editions = 50
    edition_price = 1000000
    royalties = 100

    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions)

    # Check that the swaps big map is correct
    scenario.verify(marketplaceV3.data.swaps.contains(0))
    scenario.verify(marketplaceV3.data.swaps[0].issuer == artist1.address)
    scenario.verify(marketplaceV3.data.swaps[0].fa2 == objkt.address)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_id == objkt_id)
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions)
    scenario.verify(marketplaceV3.data.swaps[0].xtz_per_objkt == sp.mutez(edition_price))
    scenario.verify(marketplaceV3.data.swaps[0].royalties == royalties)
    scenario.verify(marketplaceV3.data.swaps[0].creator == artist1.address)

    # Check that collecting fails if the exact tez amount is not provided
    scenario += marketplaceV3.collect(0).run(valid=False, sender=collector1, amount=sp.mutez(edition_price - 1))
    scenario += marketplaceV3.collect(0).run(valid=False, sender=collector1, amount=sp.mutez(edition_price + 1))

    # Collect the OBJKT with two different collectors
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.collect(0).run(sender=collector2, amount=sp.mutez(edition_price))

    # Check that all the tez have been sent and the swaps big map has been updated
    scenario.verify(marketplaceV3.balance == sp.mutez(0))
    scenario.verify(marketplaceV3.data.swaps[0].objkt_amount == swapped_editions - 2)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - swapped_editions)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == swapped_editions - 2)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)
    scenario.verify(objkt.data.ledger[(collector2.address, objkt_id)].balance == 1)

    # Check that only the swapper can cancel the swap
    scenario += marketplaceV3.cancel_swap(0).run(valid=False, sender=collector1)
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Check that the OBJKT ledger information is correct
    scenario.verify(objkt.data.ledger[(artist1.address, objkt_id)].balance == editions - 2)
    scenario.verify(objkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == 0)
    scenario.verify(objkt.data.ledger[(collector1.address, objkt_id)].balance == 1)
    scenario.verify(objkt.data.ledger[(collector2.address, objkt_id)].balance == 1)

    # Check that the swaps big map has been updated
    scenario.verify(~marketplaceV3.data.swaps.contains(0))

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

    # Swap the OBJKT in the marketplace v3 contract
    objkt_id = 152
    swapped_editions = 50
    edition_price = 0
    royalties = 100

    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

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

    # Swap the OBJKT in the marketplace v3 contract
    objkt_id = 152
    swapped_editions = 50
    edition_price = 2
    royalties = 100

    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

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

    # Check that only the admin can update the fees
    new_fee = 100
    scenario += marketplaceV3.update_fee(new_fee).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_fee(new_fee).run(sender=admin)

    # Check that the fee is updated
    scenario.verify(marketplaceV3.data.fee == new_fee)

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

    # Check that only the admin can update the fee recipient
    new_fee_recipient = artist1.address
    scenario += marketplaceV3.update_fee_recipient(new_fee_recipient).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_fee_recipient(new_fee_recipient).run(sender=admin)

    # Check that the fee recipient is updated
    scenario.verify(marketplaceV3.data.fee_recipient == new_fee_recipient)

@sp.add_test(name="Test update manager")
def test_update_manager():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Check that only the admin can update the manager
    new_manager = artist1.address
    scenario += marketplaceV3.update_manager(new_manager).run(valid=False, sender=artist1)
    scenario += marketplaceV3.update_manager(new_manager).run(sender=admin)

    # Check that the manager is updated
    scenario.verify(marketplaceV3.data.manager == new_manager)

    # Check that only the new manager can update the manager
    new_manager = artist2.address
    scenario += marketplaceV3.update_manager(new_manager).run(valid=False, sender=admin)
    scenario += marketplaceV3.update_manager(new_manager).run(sender=artist1)

    # Check that the manager is updated
    scenario.verify(marketplaceV3.data.manager == new_manager)

@sp.add_test(name="Test add and remove fa2")
def test_add_and_remove_fa2():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    admin = testEnvironment["admin"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
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

    # Check that is not possible to swap this token
    swapped_editions = 50
    edition_price = 1000000
    royalties = 100

    scenario += newobjkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=newobjkt.address,
        objkt_id=objkt_id,
        objkt_amount=swapped_editions,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=objkt_id))]).run(sender=artist1)

    # Check that only the admin can update the fa2 list
    new_fa2 = newobjkt.address
    scenario += marketplaceV3.add_fa2(new_fa2).run(valid=False, sender=artist1)
    scenario += marketplaceV3.add_fa2(new_fa2).run(sender=admin)

    # Check that the new FA2 token is now part of the allowed FA2 contracts
    scenario.verify(marketplaceV3.data.allowed_fa2s[objkt.address])
    scenario.verify(marketplaceV3.data.allowed_fa2s[new_fa2])

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
    scenario += marketplaceV3.remove_fa2(newobjkt.address).run(sender=admin)

    # Check that now is not allowed to trade newOBJKT tokens
    scenario.verify(marketplaceV3.data.allowed_fa2s[objkt.address])
    scenario.verify(~marketplaceV3.data.allowed_fa2s[newobjkt.address])
    scenario += marketplaceV3.swap(
        fa2=newobjkt.address,
        objkt_id=objkt_id,
        objkt_amount=1,
        xtz_per_objkt=sp.mutez(edition_price),
        royalties=royalties,
        creator=artist1.address).run(valid=False, sender=artist1)

    # Check that however it is possible to collect the previous swap and to cancel it
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(edition_price))
    scenario += marketplaceV3.cancel_swap(0).run(sender=artist1)

    # Check that the newOBJKT ledger information is correct
    scenario.verify(newobjkt.data.ledger[(artist1.address, objkt_id)].balance == editions - 1)
    scenario.verify(newobjkt.data.ledger[(marketplaceV3.address, objkt_id)].balance == 0)
    scenario.verify(newobjkt.data.ledger[(collector1.address, objkt_id)].balance == 1)
