// Clear localStorage for hivebot demo
// Run this in browser console on localhost:3000/demo

console.log('🧹 Clearing Hivebot Demo localStorage...');

// Clear specific demo keys
const keysToDelete = [
    'user_strategy_metadata',
    'demo_state',
    'hivebot_demo_data'
];

keysToDelete.forEach(key => {
    if (localStorage.getItem(key)) {
        localStorage.removeItem(key);
        console.log(`✅ Cleared: ${key}`);
    } else {
        console.log(`ℹ️ Not found: ${key}`);
    }
});

// Show remaining localStorage items
console.log('📋 Remaining localStorage items:');
for (let i = 0; i < localStorage.length; i++) {
    const key = localStorage.key(i);
    console.log(`  - ${key}: ${localStorage.getItem(key)?.substring(0, 50)}...`);
}

console.log('✅ localStorage cleanup complete! Refresh the page.');