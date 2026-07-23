const fs = require('fs');
const https = require('https');
const path = require('path');

const targetDir = path.join(__dirname, 'templates', 'icons');
if (!fs.existsSync(targetDir)){
    fs.mkdirSync(targetDir, { recursive: true });
}

// Get the list of icons from test_icons.py
const { execSync } = require('child_process');
const iconStr = execSync('python test_icons.py').toString().trim();
const icons = iconStr.split(',').filter(i => i && i !== "{{ item.icon|default:'circle' }}");
// Also add 'circle' explicitly as it is used as a default
icons.push('circle');
// Map missing names that might have been deprecated
const aliases = {
    'bar-chart-2': 'chart-column',
    'bar-chart': 'chart-column'
};

https.get('https://unpkg.com/lucide@0.400.0/dist/umd/lucide.js', (res) => {
    let data = '';
    res.on('data', d => data += d);
    res.on('end', () => {
        const window = {};
        const document = {};
        eval(data);
        const lib = lucide.icons;
        
        let successCount = 0;
        let failCount = 0;
        
        icons.forEach(iconName => {
            let searchName = aliases[iconName] || iconName;
            let camel = searchName.replace(/-([a-z])/g, g => g[1].toUpperCase());
            let pascal = camel.charAt(0).toUpperCase() + camel.slice(1);
            
            let iconNode = lib[pascal] || lib[camel];
            
            if (iconNode) {
                // Generate SVG markup with Django template syntax for class
                let svg = `<svg class="{{ class|default:'w-5 h-5' }}" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\n`;
                
                iconNode.forEach(child => {
                    let attrs = Object.entries(child[1]).map(([k, v]) => `${k}="${v}"`).join(' ');
                    svg += `  <${child[0]} ${attrs}></${child[0]}>\n`;
                });
                
                svg += `</svg>`;
                
                fs.writeFileSync(path.join(targetDir, `${iconName}.html`), svg);
                successCount++;
            } else {
                console.log(`Failed to find icon: ${iconName} (searched for ${pascal})`);
                failCount++;
            }
        });
        
        console.log(`Successfully generated ${successCount} SVGs. Failed: ${failCount}`);
    });
});
