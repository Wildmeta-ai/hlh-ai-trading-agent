// Test script for new personal_sign authentication

const testAuth = async () => {
  // Test data provided by the user
  const headers = {
    'x-auth-message': 'UGxlYXNlIHNpZ24gdGhpcyBtZXNzYWdlIHRvIGF1dGhlbnRpY2F0ZSB3aXRoIEFJIFRyYWRpbmcgQm90LgoKV2FsbGV0OiAweDhjZjM5YjUzYmQ1NTMyNTY2YmM3OTU4OGEyMjcwZDUzMTc2YmQwY2UKVGltZXN0YW1wOiAxNzU4NDI0MDg2NDE5CgpUaGlzIHNpZ25hdHVyZSB3aWxsIGJlIHVzZWQgZm9yIEFQSSBhdXRoZW50aWNhdGlvbi4=',
    'x-auth-signature': '0xa6cd04b8e5726c552c6198fa0c69e8ef46ee48ed8b574d067b7d55586a2b34067aa8d100245724ba87d7f8fc811d83b945cd79f12b2d1a91d6714ab5be44e4b11c',
    'x-wallet-address': '0x8cf39b53bd5532566bc79588a2270d53176bd0ce'
  };

  // Decode the message to show what we're verifying
  const messageBuffer = Buffer.from(headers['x-auth-message'], 'base64');
  const decodedMessage = messageBuffer.toString('utf-8');

  console.log('Testing authentication with new personal_sign format');
  console.log('================================================');
  console.log('\nDecoded message:');
  console.log(decodedMessage);
  console.log('\nWallet:', headers['x-wallet-address']);
  console.log('Signature:', headers['x-auth-signature']);

  // Test against the API
  try {
    const response = await fetch('http://localhost:8091/api/strategies', {
      method: 'GET',
      headers: headers
    });

    const responseData = await response.text();

    console.log('\n\nAPI Response:');
    console.log('Status:', response.status);
    console.log('Response:', responseData);

    if (response.ok) {
      console.log('\n✅ Authentication successful!');
    } else {
      console.log('\n❌ Authentication failed');
      const errorData = JSON.parse(responseData);
      console.log('Error:', errorData.error);
      console.log('Details:', errorData.details);
    }
  } catch (error) {
    console.error('\n❌ Request failed:', error.message);
  }
};

// Run the test
testAuth();