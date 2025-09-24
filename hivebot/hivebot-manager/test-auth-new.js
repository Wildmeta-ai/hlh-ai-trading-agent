// Test script for new personal_sign authentication with fresh signature

const testAuth = async () => {
  // Fresh headers with current timestamp from user
  const headers = {
    'x-auth-message': 'UGxlYXNlIHNpZ24gdGhpcyBtZXNzYWdlIHRvIGF1dGhlbnRpY2F0ZSB3aXRoIEFJIFRyYWRpbmcgQm90LgoKV2FsbGV0OiAweDhjZjM5YjUzYmQ1NTMyNTY2YmM3OTU4OGEyMjcwZDUzMTc2YmQwY2UKVGltZXN0YW1wOiAxNzU4NDI5NTgxMjE1CgpUaGlzIHNpZ25hdHVyZSB3aWxsIGJlIHVzZWQgZm9yIEFQSSBhdXRoZW50aWNhdGlvbi4=',
    'x-auth-signature': '0x5760538db6fdabb9558c3e733d47d18f6767b0460b71fa04356dad81695627e865238367bf7a2f8a67ed412a03f5635369bc9d86e09529edf7351abea92496b21b',
    'x-wallet-address': '0x8cf39b53bd5532566bc79588a2270d53176bd0ce'
  };

  // Decode the message to show what we're verifying
  const messageBuffer = Buffer.from(headers['x-auth-message'], 'base64');
  const decodedMessage = messageBuffer.toString('utf-8');

  console.log('Testing authentication with NEW personal_sign signature');
  console.log('====================================================');
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

    if (response.ok) {
      console.log('\n✅ Authentication successful!');
      console.log('Response data:', responseData);
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