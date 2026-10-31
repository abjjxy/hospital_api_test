// Jenkinsfile
// ==========================================================================
// Jenkins 流水线：与 .github/workflows/api-test.yml 等价，只是换成 Groovy 语法
//
// 结构对照：
//   agent    → runs-on
//   stages   → jobs / steps
//   parameters → workflow_dispatch 的 inputs
//   triggers → on: schedule / push
//   post     → upload-artifact + 报告发布
// ==========================================================================
pipeline {

    // 用 python 官方镜像执行，这样 Jenkins 主机上不用装 Python
    // 前置要求：启动 Jenkins 容器时挂载 docker.sock（见 README）
    agent {
        docker {
            image 'python:3.12'
            args '-u root'
            reuseNode true
        }
    }

    environment {
        // 国内网络下用清华 PyPI 镜像，装依赖会快很多；海外环境可删除这一行
        PIP_INDEX_URL = 'https://pypi.tuna.tsinghua.edu.cn/simple'
    }

    // ----------------------------------------------------------------------
    // 构建参数：相当于 Actions 的 workflow_dispatch inputs
    // 注意：参数化构建要在第一次构建成功之后，参数才会出现在「Build with Parameters」里
    // ----------------------------------------------------------------------
    parameters {
        choice(name: 'ENV', choices: ['dev', 'test', 'prod'], description: '运行环境')
        string(name: 'MARKER', defaultValue: '', description: 'pytest -m 过滤：smoke / regression / negative，留空跑全部')
        string(name: 'KEYWORD', defaultValue: '', description: 'pytest -k 用例名关键字过滤，留空不过滤')
    }

    options {
        timestamps()                                    // 每行日志前面加时间戳
        timeout(time: 20, unit: 'MINUTES')              // 超时保护
        disableConcurrentBuilds()                       // 同一 job 不允许并发
        buildDiscarder(logRotator(numToKeepStr: '20', artifactNumToKeepStr: '10'))
    }

    // ----------------------------------------------------------------------
    // 定时触发：H 18 * * * 表示每天 18 点左右执行
    // H 是 Jenkins 的哈希占位符，用来把任务错峰，避免整点一起跑
    // 时区取决于 Jenkins 服务器的时区设置
    // ----------------------------------------------------------------------
    triggers {
        cron('H 18 * * *')
    }

    stages {

        stage('环境检查') {
            steps {
                sh 'python --version'
                sh 'pip --version'
            }
        }

        stage('安装依赖') {
            steps {
                sh 'pip install -U pip'
                sh 'pip install -r requirements.txt'
            }
        }

        // 等价于 Actions 里的 "执行接口测试" step
        stage('执行接口测试') {
            steps {
                script {
                    def args = "--env=${params.ENV} --junitxml=reports/junit.xml"

                    if (params.MARKER?.trim()) {
                        args += " -m '${params.MARKER.trim()}'"
                    }
                    if (params.KEYWORD?.trim()) {
                        args += " -k '${params.KEYWORD.trim()}'"
                    }

                    echo "执行命令：pytest ${args}"
                    sh "pytest ${args}"
                }
            }
        }
    }

    // ----------------------------------------------------------------------
    // post 阶段：无论成功失败都会执行（等价于 Actions 的 if: always()）
    // 这是测试类项目最重要的一段 —— 失败时也要能看到报告
    // ----------------------------------------------------------------------
    post {
        always {
            // JUnit 报告：Jenkins 内置支持，构建页面会显示失败用例趋势图
            junit testResults: 'reports/junit.xml', allowEmptyResults: true

            // Allure 报告：需要安装 Allure Jenkins Plugin，
            // 并在「Manage Jenkins → Tools → Allure Commandline」里配置一个工具实例
            allure includeProperties: false, jdk: '', results: [[path: 'reports/allure-results']]

            // 备用方案：没装 Allure 插件时，用 HTML Publisher 也能看
            // publishHTML(target: [
            //     reportDir: 'reports/allure-report',
            //     reportFiles: 'index.html',
            //     reportName: 'Allure Report'
            // ])

            // 归档原始产物，随时可下载
            archiveArtifacts artifacts: 'reports/**', allowEmptyArchive: true
        }

        success {
            echo '✅ 接口测试全部通过'
        }

        failure {
            echo '❌ 存在失败用例，请查看 Allure 报告'
            // TODO 需要告警时在这里加企业微信 / 钉钉机器人推送
            // sh 'curl -s -X POST "$WEBHOOK_URL" -H "Content-Type: application/json" -d "{\"msgtype\":\"text\",\"text\":{\"content\":\"接口测试失败: $BUILD_URL\"}}"'
        }

        cleanup {
            // 清理工作区，下次构建从干净状态开始（避免残留报告互相干扰）
            cleanWs()
        }
    }
}