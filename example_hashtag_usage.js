const TikTokHashtagMonitor = require('./tiktok/tiktok_hashtag_monitor');

async function exampleUsage() {
    const sessionCookie = 'd28edfbdf343b06ed26cc0430e5eba2d';
    const monitor = new TikTokHashtagMonitor(sessionCookie);

    console.log('🎯 TikTok Hashtag Traffic Monitor - Example Usage\n');

    try {
        // Example 1: Monitor a single trending hashtag
        console.log('📍 Example 1: Monitoring single hashtag');
        await monitor.monitorHashtag('love', 30);

        console.log('\n⏱️ Waiting 10 seconds before next example...\n');
        await new Promise(resolve => setTimeout(resolve, 10000));

        // Example 2: Monitor multiple hashtags for comparison
        console.log('📍 Example 2: Monitoring multiple hashtags');
        const trendingHashtags = ['dance', 'music', 'funny', 'trending'];
        await monitor.monitorMultipleHashtags(trendingHashtags, 20);

    } catch (error) {
        console.error('❌ Example failed:', error.message);
    }
}

// Custom analysis example
async function customAnalysisExample() {
    const sessionCookie = 'd28edfbdf343b06ed26cc0430e5eba2d';
    const monitor = new TikTokHashtagMonitor(sessionCookie);

    console.log('🔬 Custom Analysis Example\n');

    try {
        // Get data for analysis
        const result = await monitor.monitorHashtag('viral', 50);
        
        if (result.metrics) {
            // Custom analysis
            const metrics = result.metrics;
            
            console.log('🧮 Custom Analysis Results:');
            console.log(`   Viral Potential Score: ${calculateViralScore(metrics)}/100`);
            console.log(`   Creator Diversity: ${Object.keys(metrics.topCreators).length} unique creators in top posts`);
            console.log(`   Recent Activity: ${metrics.recentActivity.length} videos in last 7 days`);
            
            // Identify trending patterns
            if (metrics.avgViews > 100000) {
                console.log('🔥 HIGH TRAFFIC: This hashtag is experiencing high engagement!');
            } else if (metrics.avgViews > 50000) {
                console.log('📈 MODERATE TRAFFIC: Steady engagement on this hashtag');
            } else {
                console.log('📊 LOW TRAFFIC: Niche or emerging hashtag');
            }
        }

    } catch (error) {
        console.error('❌ Custom analysis failed:', error.message);
    }
}

function calculateViralScore(metrics) {
    // Simple viral potential scoring algorithm
    let score = 0;
    
    // Engagement rate (0-40 points)
    score += Math.min(parseFloat(metrics.engagementRate) * 4, 40);
    
    // Average views (0-30 points) 
    score += Math.min(metrics.avgViews / 10000, 30);
    
    // Recent activity (0-20 points)
    score += Math.min(metrics.recentActivity.length * 2, 20);
    
    // Creator diversity (0-10 points)
    score += Math.min(Object.keys(metrics.topCreators).length, 10);
    
    return Math.round(score);
}

// Run examples
async function runExamples() {
    console.log('🚀 Starting TikTok Hashtag Monitor Examples\n');
    
    // Uncomment the example you want to run:
    
    // Basic usage example
    // await exampleUsage();
    
    // Custom analysis example  
    await customAnalysisExample();
    
    console.log('✅ Examples completed!');
}

if (require.main === module) {
    runExamples().catch(console.error);
}

module.exports = { exampleUsage, customAnalysisExample, calculateViralScore };


