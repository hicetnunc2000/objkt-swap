"""Unit tests for the Marketplace v1 class.

"""

import smartpy as sp
import os

# Import the FA2 and marketplaces modules
fa2Contract = sp.io.import_script_from_url(f"file://{os.getcwd()}/fa2.py")
marketplaceContractV1 = sp.io.import_script_from_url(f"file://{os.getcwd()}/objkt_swap_v1.py")


def get_test_environment():
    # Create the test accounts
    admin = sp.test_account("admin")
    artist1 = sp.test_account("artist1")
    artist2 = sp.test_account("artist2")

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

    # Add all the contracts to the test scenario
    scenario = sp.test_scenario()
    scenario += objkt
    scenario += hdao
    scenario += curate
    scenario += marketplaceV1

    # Change the OBJKT token administrator to the marketplace v1 contract
    scenario += objkt.set_administrator(marketplaceV1.address).run(sender=admin)

    # Save all the variables in a test environment dictionary
    testEnvironment = {
        "scenario" : scenario,
        "admin" : admin,
        "artist1" : artist1,
        "artist2" : artist2,
        "objkt" : objkt,
        "hdao" : hdao,
        "curate" : curate,
        "marketplaceV1" : marketplaceV1}

    return testEnvironment


@sp.add_test(name="Test mint failure conditions")
def test_mint_failure_conditions():
    # Get the test environment
    testEnvironment = get_test_environment()
    scenario = testEnvironment["scenario"]
    artist1 = testEnvironment["artist1"]
    artist2 = testEnvironment["artist2"]
    objkt = testEnvironment["objkt"]
    marketplaceV1 = testEnvironment["marketplaceV1"]

    # Check that we start with the correct genesis number
    scenario.verify(marketplaceV1.data.objkt_id == 152)

    # Check that minting an OBJKT with 0 copies fails
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=0,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1, valid=False)

    # Check that minting an OBJKT with too many copies also fails
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=100000,
        metadata=sp.pack("ipfs://fff"),
        royalties=100).run(sender=artist1, valid=False)

    # Check that trying to mint an objkt on behalf of someone else fails
    #scenario += marketplaceV1.mint_OBJKT(
    #    address=artist1.address,
    #    amount=1,
    #    metadata=sp.pack("ipfs://fff"),
    #    royalties=200).run(sender=artist2.address, valid=False)

    # Check that minting an objkt with too many royalties fails
    scenario += marketplaceV1.mint_OBJKT(
        address=artist1.address,
        amount=2,
        metadata=sp.pack("ipfs://fff"),
        royalties=300).run(sender=artist1.address, valid=False)

    # objkt number must not have changed
    scenario.verify(marketplaceV1.data.objkt_id == 152)
