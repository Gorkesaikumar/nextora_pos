const fs = require('fs');
const path = require('path');
const lucide = require('lucide');

const targetDir = path.join(__dirname, 'templates', 'icons');
if (!fs.existsSync(targetDir)){
    fs.mkdirSync(targetDir, { recursive: true });
}

const { execSync } = require('child_process');
const iconStr = execSync('python test_icons.py').toString().trim();
const icons = iconStr.split(',').filter(i => i && i !== "{{ item.icon|default:'circle' }}");
icons.push('circle'); // default fallback

const aliases = {
    'bar-chart-2': 'chart-column',
    'bar-chart': 'chart-column',
    'bar-chart-3': 'chart-column-increasing',
    'building-2': 'building-2',
    'check-circle-2': 'circle-check-big',
    'lifebuoy': 'life-buoy',
};

const lib = Object.keys(lucide.icons).reduce((acc, key) => {
    acc[key.toLowerCase()] = lucide.icons[key];
    return acc;
}, {});

let successCount = 0;
let failCount = 0;

icons.forEach(iconName => {
    let searchName = aliases[iconName] || iconName;
    // Remove dashes completely to match lowercase keys
    let lookup = searchName.replace(/-/g, '').toLowerCase();
    
    let iconNode = lib[lookup];
    
    if (iconNode) {
        let svg = `<svg class="{{ class|default:'w-5 h-5 text-neutral-400' }}" xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">\n`;
        
        iconNode.forEach(child => {
            let attrs = Object.entries(child[1]).map(([k, v]) => `${k}="${v}"`).join(' ');
            svg += `  <${child[0]} ${attrs}></${child[0]}>\n`;
        });
        
        svg += `</svg>`;
        
        fs.writeFileSync(path.join(targetDir, `${iconName}.html`), svg);
        successCount++;
    } else {
        console.log(`Failed to find icon: ${iconName} (searched for ${lookup})`);
        failCount++;
    }
});

console.log(`Successfully generated ${successCount} SVGs. Failed: ${failCount}`);
