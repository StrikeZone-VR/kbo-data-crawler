import pandas as pd

# 데이터 로드
df = pd.read_csv('kbo_hitters_2020_2025.csv')

# 컬럼명 확인
print("컬럼명:", df.columns.tolist())
print()

# 선수별 홈런 합계 계산 (HR이 홈런 컬럼)
hr_ranking = df.groupby('선수명')['HR'].sum().sort_values(ascending=False)

print("🏆 KBO 2020-2025 홈런왕 순위 🏆")
print("=" * 40)

for i, (player, hrs) in enumerate(hr_ranking.head(20).items(), 1):
    print(f"{i:2d}. {player:<12} {hrs:3d}개")