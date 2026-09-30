*** Settings ***
Library    PlatynUI.BareMetal


*** Variables ***
${CALCULATOR}    //control:Window[@Name='Calculator']
${RESULT}        //control:Text[@AutomationId='CalculatorResults']


*** Test Cases ***
One Plus Two Is Three
    Activate Window    ${CALCULATOR}
    Pointer Click    ${CALCULATOR}//control:Button[@Name='One']
    Pointer Click    ${CALCULATOR}//control:Button[@Name='Plus']
    Pointer Click    ${CALCULATOR}//control:Button[@Name='Two']
    Pointer Click    ${CALCULATOR}//control:Button[@Name='Equals']
    ${shown}=    Get Attribute    ${RESULT}    Name
    Should Contain    ${shown}    3
