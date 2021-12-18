"""Unit tests for the Marketplace v2 class.

"""

import smartpy as sp
import os

# Import the FA2 and marketplaces modules
fa2Contract = sp.io.import_script_from_url(f"file://{os.getcwd()}/fa2.py")
marketplaceContractV1 = sp.io.import_script_from_url(
    f"file://{os.getcwd()}/objkt_swap_v1.py")
marketplaceContractV2 = sp.io.import_script_from_url(
    f"file://{os.getcwd()}/objkt_swap_v2.py")


def get_test_environment():
    # Create the test accounts
    admin = sp.test_account("admin")
    artist1 = sp.test_account("artist1")
    collector1 = sp.test_account("collector1")

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

    # Initialize a dummy curate contract
    curate = sp.Contract()

    # Initialize the marketplace v1 contract
    marketplaceV1 = marketplaceContractV1.OBJKTSwap(
        objkt=objkt.address,
        hdao=hdao.address,
        manager=admin.address,
        metadata=sp.utils.metadata_of_url("ipfs://ccc"),
        curate=curate.address)

    # Initialize the marketplace v2 contract
    marketplaceV2 = marketplaceContractV2.Marketplace(
        objkt=objkt.address,
        metadata=sp.utils.metadata_of_url("ipfs://ddd"),
        manager=admin.address,
        fee=25)

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += objkt
    scenario += hdao
    scenario += curate
    scenario += marketplaceV1
    scenario += marketplaceV2

    # Change the OBJKT token administrator to the marketplace v1 contract
    scenario += objkt.set_administrator(marketplaceV1.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "admin" : admin,
        "artist1" : artist1,
        "collector1" : collector1,
        "objkt" : objkt,
        "hdao" : hdao,
        "curate" : curate,
        "marketplaceV1" : marketplaceV1,
        "marketplaceV2" : marketplaceV2}

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
    marketplaceV2 = testEnvironment["marketplaceV2"]

    # Mint an OBJKT
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100,
        metadata=sp.pack("ipfs://eee"),
        royalties=100).run(sender=artist1)

    # Swap the OBJKT in the marketplace v2 contract
    scenario += objkt.update_operators(
        [sp.variant("add_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV2.address,
            token_id=152))]).run(sender=artist1)
    scenario += marketplaceV2.swap(
        objkt_amount=50,
        objkt_id=152,
        xtz_per_objkt=sp.tez(1),
        royalties=100,
        creator=artist1.address).run(sender=artist1)
    scenario += objkt.update_operators(
        [sp.variant("remove_operator", objkt.operator_param.make(
            owner=artist1.address,
            operator=marketplaceV2.address,
            token_id=152))]).run(sender=artist1)

    # Collect the OBJKT
    scenario += marketplaceV2.collect(
        swap_id=500000).run(sender=collector1, amount=sp.tez(1))

    # Check that all the tez have been sent
    scenario.verify(marketplaceV2.balance == sp.mutez(0))
