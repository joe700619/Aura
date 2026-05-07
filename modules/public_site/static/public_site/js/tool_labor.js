// 勞健保試算
(function () {
  'use strict';
  const LABOR_GRADES = [27470,28800,30300,31800,33300,34800,36300,38200,40100,42000,43900,45800,48200,50600,53000,55400,57800];
  const HEALTH_GRADES = LABOR_GRADES.concat([60800,63800,66800,69800,72800,76500,80200,83900,87600,92100,96600,101100,105600,110100,115500,120900,126300,131700]);

  function bracket(salary, grades) {
    for (const g of grades) if (salary <= g) return g;
    return grades[grades.length - 1];
  }
  const fmt = (n) => Math.round(n).toLocaleString();
  const moneyText = (n) => fmt(n) + ' 元';

  const salaryEl = document.getElementById('li-salary');
  const depsEl = document.getElementById('li-deps');

  function recalc() {
    const salary = parseInt(salaryEl.value) || 0;
    let deps = parseInt(depsEl.value) || 0;
    if (deps < 0) deps = 0;
    if (deps > 3) { deps = 3; depsEl.value = 3; }

    const laborGrade = bracket(salary, LABOR_GRADES);
    const healthGrade = bracket(salary, HEALTH_GRADES);

    const laborTotal = Math.round(laborGrade * 0.115);
    const laborEmp = Math.round(laborTotal * 0.20);
    const laborEr = Math.round(laborTotal * 0.70);

    const healthBase = healthGrade * 0.0517;
    const healthEmpBase = Math.round(healthBase * 0.30);
    const healthEmp = healthEmpBase * (1 + deps);
    const healthEr = Math.round(healthBase * 0.60 * (1 + 0.57));

    const pension = Math.round(salary * 0.06);

    const empTotal = laborEmp + healthEmp;
    const erTotal = laborEr + healthEr + pension;
    const grand = empTotal + erTotal;

    document.getElementById('li-labor-grade').textContent = moneyText(laborGrade);
    document.getElementById('li-health-grade').textContent = moneyText(healthGrade);
    document.getElementById('li-emp').textContent = fmt(empTotal);
    document.getElementById('li-er').textContent = fmt(erTotal);
    document.getElementById('li-grand').textContent = fmt(grand);
    document.getElementById('li-labor-emp').textContent = moneyText(laborEmp);
    document.getElementById('li-labor-er').textContent = moneyText(laborEr);
    document.getElementById('li-health-emp').textContent = moneyText(healthEmp);
    document.getElementById('li-health-emp-label').textContent = `員工自付（含 ${deps} 位眷屬）`;
    document.getElementById('li-health-er').textContent = moneyText(healthEr);
    document.getElementById('li-pension').textContent = moneyText(pension);
  }

  ['input', 'change'].forEach((ev) => {
    salaryEl.addEventListener(ev, recalc);
    depsEl.addEventListener(ev, recalc);
  });
  recalc();
})();
