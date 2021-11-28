"""Unit tests for the Marketplace v3 class.

"""

import smartpy as sp

# Import the FA2 and marketplaces modules
fa2Contract = sp.io.import_script_from_url("file:smart-py/fa2.py")
marketplaceContractV1 = sp.io.import_script_from_url(
    "file:smart-py/objkt_swap_v1.py")
marketplaceContractV3 = sp.io.import_script_from_url(
    "file:smart-py/objkt_swap_v3.py")


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
        objkt=objkt.address,
        fee=25)

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += objkt
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
    collector1 = testEnvironment["collector1"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]
    marketplaceV3 = testEnvironment["marketplaceV3"]

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Swap the OBJKT in the marketplace v3 contract
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=50,
        xtz_per_objkt=sp.tez(1),
        royalties=100,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.tez(1))

    # Check that all the tez have been sent
    scenario.verify(marketplaceV3.balance == sp.mutez(0))

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
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Swap the OBJKT in the marketplace v3 contract
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=50,
        xtz_per_objkt=sp.tez(0),
        royalties=100,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.tez(0))

    # Check that all the tez have been sent
    scenario.verify(marketplaceV3.balance == sp.mutez(0))

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
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1)

    # Swap the OBJKT in the marketplace v3 contract
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)
    scenario += marketplaceV3.swap(
        fa2=objkt.address,
        objkt_id=152,
        objkt_amount=50,
        xtz_per_objkt=sp.mutez(2),
        royalties=100,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV3.address,
            token_id=152))]).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV3.collect(0).run(sender=collector1, amount=sp.mutez(2))

    # Check that all the tez have been sent
    scenario.verify(marketplaceV3.balance == sp.mutez(0))
