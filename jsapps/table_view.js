
function fillColumnsSelect(columns) {
    let html = ''
    for (let index in columns) {
        html += `<option>${index}: ${columns[index]}</option>\n`
    }
    return html
}

function fillSessionsSelect(sessions) {
    let html = ''
    for (let sessionId of sessions) {
        html += `<option>${sessionId}</option>\n`
    }
    return html
}

function generateTable(columns, rows) {
    let table = '<table class="table table-bordered table-hover table-sm">'
    table += '<thead><tr>'
    for (let index in columns) {
        table += `<th><span>${columns[index]}</span></th>\n`
    }
    table += '</tr></thead>'
    for (let dataLine of rows) {
        let line = '<tr>'
        for (let dataItem of dataLine) {
            let value = isFloat(dataItem) ? dataItem.toFixed(3) : dataItem
            line += '<td>' + value + '</td>'
        }
        line += '</tr>\n'
        table +=  line
    }
    table += '</table>'
    return table
}

class TableView {
  constructor(table) {
    this.table = table
    this.rowsCount = table.length
  }

  filterAllEqual(row, filterParams) {
    for (const columnIndex in filterParams) {
      if (row[columnIndex] != filterParams[columnIndex]) {
        return false
      }
    }
    return true
  }

  getColumn(index, filterParams) {
    let column = []
    for (const row of this.table) {
      if (this.filterAllEqual(row, filterParams)) {
        column.push(row[index])
      }
    }
    return column
  }
}

function excludeNaN(items) {
    let out = []
    for (const item of items) {
        if (!isNaN(item)) {
            out.push(item)
        }
    }
    return out
}

function isFloat(n) {
    return n === +n && n !== (n|0)
}

function valuesToStr(items) {
    let out = []
    for (const item of items) {
        out.push(isFloat(item) ? item.toFixed(2) : item)
    }
    return out.join(', ')
}

function mean2(items) {
    let sum = 0
    for (const item of items) {
        sum += item
    }
    return sum / items.length
}

function stdev(items) {
    const n = items.length
    const mean = items.reduce((a, b) => a + b) / n
    return Math.sqrt(items.map(x => Math.pow(x - mean, 2)).reduce((a, b) => a + b) / n)
}

function parserGroupDef(src) {
    let out = {}
    for (const pair of src.split(',')) {
        const [column, value ] = pair.split(':')
        out[column.trim()] = value.trim()
    }
    return out
}

function analyseTTest() {
    const group1Def = parserGroupDef(document.getElementById('group1Def').value)
    const group2Def = parserGroupDef(document.getElementById('group2Def').value)
    let dataView = new TableView(selected_session)
    let out = ''
    for (let k = 5; k <= 32; k++) {
        const group1NaN = dataView.getColumn(k, group1Def)
        const group2NaN = dataView.getColumn(k, group2Def)
        const group1 = excludeNaN(group1NaN)
        const group2 = excludeNaN(group2NaN)
        const g1NaNs = (group1NaN.length - group1.length) > 0 ? ` (${group1NaN.length - group1.length} n/n)` : ''
        const g2NaNs = (group2NaN.length - group2.length) > 0 ? ` (${group2NaN.length - group2.length} n/n)` : ''
        if (group1.length > 0 && group2.length > 0) {
            const result = ttest2(group1, group2)
            const signifClass = result.pValue < 0.05 ? 'signifRow' : ''
            out += `<tr class="${signifClass}">
                <td><b>${resultsColumns[k]}</b></td>
                <td title="Values: ${valuesToStr(group1)}"><b><span class="title">${group1.length}${g1NaNs}</span></b></td>
                <td>${mean2(group1).toFixed(2)}</td>
                <td>${stdev(group1).toFixed(2)}</td>
                <td title="Values: ${valuesToStr(group2)}"><b><span class="title">${group2.length}${g2NaNs}</span></b></td>
                <td>${mean2(group2).toFixed(2)}</td>
                <td>${stdev(group2).toFixed(2)}</td>
                <td>${result.statistic.toFixed(4)}</td>
                <td><b>${result.pValue.toFixed(4)}<b></td>
            </tr>`
        } else {
            out += `<tr>
                <td><b>${resultsColumns[k]}</b></td>
                <td title="Values: ${valuesToStr(group1)}"><b><span class="title">${group1.length}${g1NaNs}</span></b></td>
                <td>NaN</td>
                <td>NaN</td>
                <td title="Values: ${valuesToStr(group2)}"><b><span class="title">${group2.length}${g2NaNs}</span></b></td>
                <td>NaN</td>
                <td>NaN</td>
                <td>NaN</td>
                <td><b>NaN<b></td>
            </tr>`
        }
        // console.log(result.statistic, result.pValue)
    }
    document.getElementById('statsResultPanel').classList.remove('hidden')
    document.getElementById('resultsTbody').innerHTML = out
}

document.getElementById('analyseTTestButton').addEventListener('click', analyseTTest)

document.getElementById('hideStatisticsResults').addEventListener('click', () => {
    document.getElementById('statsResultPanel').classList.add('hidden')
})

let session_ids = Object.keys(resultsData)
let selected_session = []
if (session_ids.includes('rest')) {
    selected_session = resultsData['rest']
} else {
    selected_session = resultsData[session_ids[0]]
}

function onLoad() {
    document.getElementById('summarySessions').innerHTML = fillSessionsSelect(session_ids)
    document.getElementById('summaryColumns').innerHTML = fillColumnsSelect(resultsColumns)
    document.getElementById('mainTablePanel').innerHTML = generateTable(resultsColumns, selected_session)
}
window.onload = onLoad
