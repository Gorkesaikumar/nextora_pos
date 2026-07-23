const fs = require('fs');
const path = require('path');
const lucide = require('lucide');

const targetDir = path.join(__dirname, 'templates', 'icons');
const missing = ['shopping-cart', 'list-tree', 'file-cog', 'file-check', 'list-plus', 'calendar-off', 'calendar-clock', 'sliders-horizontal', 'files', 'layout-dashboard', 'bar-chart', 'layout-grid', 'utensils-crossed', 'briefcase', 'tags', 'heart-handshake', 'clipboard-list'];

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

missing.forEach(iconName => {
    let searchName = aliases[iconName] || iconName;
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
